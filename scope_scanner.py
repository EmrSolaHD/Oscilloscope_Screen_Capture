"""
╔══════════════════════════════════════════════════════════════════════════╗
║              Oscilloscope / Instrument Network & USB Scanner            ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Discovers SCPI-capable instruments via:                                ║
║    • Ethernet — TCP port sweep across a subnet or IP range              ║
║    • USB      — USB-TMC devices via PyVISA                              ║
║                                                                         ║
║  For every instrument found, reports:                                   ║
║    IP / VISA resource, open port, *IDN? response, vendor, model        ║
║                                                                         ║
║  Usage:  python scope_scanner.py                                        ║
║          (edit SCAN_* variables below to narrow / widen the search)    ║
╚══════════════════════════════════════════════════════════════════════════╝

 Dependencies:
   pip install -r requirements.txt
"""

# ═══════════════════════════ USER CONFIGURATION ════════════════════════════ #

# ── What to scan ──────────────────────────────────────────────────────────── #
SCAN_ETHERNET = True          # Scan the local subnet via TCP
SCAN_USB      = True          # Scan USB-TMC devices via VISA

# ── Ethernet scan settings ───────────────────────────────────────────────── #
# Leave SUBNET = "" to auto-detect the local /24 subnet from the active NIC.
# Or specify explicitly, e.g.:  "192.168.1.0/24"  or  "10.0.0.0/24"
SUBNET        = ""            # "" = auto-detect local /24

# Ports checked on each host (standard SCPI instrument ports)
SCPI_PORTS    = [5025, 1861, 80]

# Number of parallel TCP threads (increase for faster scans on large subnets)
MAX_WORKERS   = 64

# Per-host TCP connect timeout (seconds) — keep low for fast sweeps
TCP_TIMEOUT   = 0.5

# SCPI *IDN? read timeout after a port is found open (seconds)
IDN_TIMEOUT   = 3

# ── Output ───────────────────────────────────────────────────────────────── #
# Set to a file path to save results as CSV, e.g. r"C:\captures\scan.csv"
# Leave "" to print results to the console only.
CSV_OUTPUT    = ""

# ═══════════════════════════════════════════════════════════════════════════ #
#  Do NOT edit below this line unless you know what you are doing.
# ═══════════════════════════════════════════════════════════════════════════ #

import csv
import ipaddress
import os
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# ── PyVISA (optional — needed only for USB scan) ──────────────────────────
try:
    import pyvisa
    PYVISA_AVAILABLE = True
except ImportError:
    PYVISA_AVAILABLE = False


def _open_rm() -> "pyvisa.ResourceManager":
    """
    Return the best available VISA ResourceManager.

    Priority:
      1. System VISA backend (NI-VISA, Keysight IO, IVI Foundation driver)
         — required to see devices that appear as IVI in Device Manager.
      2. pyvisa-py pure-Python backend (@py)
         — fallback for machines without a system VISA installation.
    """
    try:
        rm = pyvisa.ResourceManager()   # uses system VISA (NI / Keysight / IVI)
        rm.list_resources()             # quick test — raises if backend unusable
        return rm
    except Exception:
        pass
    return pyvisa.ResourceManager("@py")


# ══════════════════════════ Helpers ══════════════════════════════════════════

def get_all_subnets() -> list[tuple[str, str]]:
    """
    Return a list of (interface_name, subnet_cidr) for every active
    IPv4 NIC — covering Wi-Fi, LAN, VPN adapters, etc.

    Falls back to a single UDP-trick detection when socket.getaddrinfo
    cannot enumerate interfaces (rare).
    Returns list of (label, '192.168.x.0/24') tuples.
    """
    subnets = []   # (label, cidr)
    seen    = set()

    # ── Method 1: psutil (most reliable, gives adapter names) ────────────
    try:
        import psutil
        for iface, addrs in psutil.net_if_addrs().items():
            stats = psutil.net_if_stats().get(iface)
            if not stats or not stats.isup:
                continue
            for addr in addrs:
                if addr.family != socket.AF_INET:
                    continue
                ip  = addr.address
                msk = addr.netmask or "255.255.255.0"
                if ip.startswith("127.") or ip == "0.0.0.0":
                    continue
                try:
                    net  = ipaddress.IPv4Network(f"{ip}/{msk}", strict=False)
                    cidr = str(net)
                    if cidr not in seen:
                        seen.add(cidr)
                        subnets.append((iface, cidr))
                except Exception:
                    pass
        if subnets:
            return subnets
    except ImportError:
        pass

    # ── Method 2: socket.getaddrinfo hostname trick ───────────────────────
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip.startswith("127."):
                continue
            try:
                net  = ipaddress.IPv4Interface(f"{ip}/24").network
                cidr = str(net)
                if cidr not in seen:
                    seen.add(cidr)
                    subnets.append((ip, cidr))
            except Exception:
                pass
        if subnets:
            return subnets
    except Exception:
        pass

    # ── Method 3: default-route UDP trick (original single-NIC method) ───
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        net  = ipaddress.IPv4Interface(f"{ip}/24").network
        return [(ip, str(net))]
    except Exception as exc:
        print(f"[ERROR] Cannot detect any local subnet: {exc}")
        print("        Set SUBNET manually, e.g.  SUBNET = '192.168.1.0/24'")
        sys.exit(1)


def tcp_probe(ip: str, port: int, timeout: float) -> bool:
    """Return True if *ip*:*port* accepts a TCP connection."""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def query_idn(ip: str, port: int, timeout: float) -> str:
    """
    Send *IDN? over a raw TCP socket and return the stripped response.
    Works for plain SCPI-over-TCP (port 5025).  Returns "" on failure.
    """
    try:
        with socket.create_connection((ip, port), timeout=timeout) as s:
            s.settimeout(timeout)
            s.sendall(b"*IDN?\n")
            time.sleep(0.2)
            chunks = []
            while True:
                try:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    if b"\n" in chunk:
                        break
                except socket.timeout:
                    break
            return b"".join(chunks).decode("ascii", errors="replace").strip()
    except Exception:
        return ""


def detect_vendor(idn: str) -> str:
    u = idn.upper()
    if "LECROY" in u or "TELEDYNE" in u:
        return "LeCroy / Teledyne"
    if "TEKTRONIX" in u:
        return "Tektronix"
    if "KEYSIGHT" in u or "AGILENT" in u:
        return "Keysight / Agilent"
    if "RIGOL" in u:
        return "Rigol"
    if "SIGLENT" in u:
        return "Siglent"
    if "ROHDE" in u:
        return "Rohde & Schwarz"
    if "NATIONAL" in u or "NI" in u:
        return "National Instruments"
    if idn:
        return "Unknown"
    return ""


def scan_host(ip: str) -> dict | None:
    """
    Probe a single host.  Returns a result dict ONLY if a valid *IDN?
    response is received, otherwise None.
    """
    for port in SCPI_PORTS:
        if not tcp_probe(ip, port, TCP_TIMEOUT):
            continue
        # Try IDN on port 5025 (plain SCPI) or 1861 (VICP)
        idn = query_idn(ip, port, IDN_TIMEOUT) if port in (5025, 1861) else ""
        if not idn:
            continue   # port responded but not a SCPI instrument — skip
        vendor = detect_vendor(idn)
        return {
            "type"    : "ETHERNET",
            "address" : ip,
            "port"    : port,
            "idn"     : idn,
            "vendor"  : vendor or "Unknown",
            "resource": f"TCPIP::{ip}::inst0::INSTR",
        }
    return None


# ══════════════════════════ Ethernet scan ════════════════════════════════════

def scan_ethernet(subnet: str, label: str = "") -> list[dict]:
    network = ipaddress.IPv4Network(subnet, strict=False)
    hosts   = list(network.hosts())
    total   = len(hosts)
    tag     = f"{label} " if label else ""

    print(f"\n[ETH] {tag}Scanning {subnet}  ({total} hosts) …")

    results  = []
    done     = 0
    found    = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(scan_host, str(h)): str(h) for h in hosts}
        for future in as_completed(futures):
            done += 1
            pct = done / total * 100
            bar = "█" * int(pct / 2) + "░" * (50 - int(pct / 2))
            print(f"\r  [{bar}] {pct:5.1f}%  found: {found}", end="", flush=True)
            result = future.result()
            if result:
                found += 1
                results.append(result)
                print(f"\r  [FOUND] {result['address']}:{result['port']}  {result['vendor']}  {result['idn'][:60]}")
                print(f"\r  [{bar}] {pct:5.1f}%  found: {found}", end="", flush=True)

    print()   # newline after progress bar
    return results


def scan_all_ethernet(subnets: list[tuple[str, str]]) -> list[dict]:
    """
    Scan every subnet in *subnets* sequentially (each with its own
    parallel host sweep).  De-duplicates by IP so overlapping adapters
    don't report the same instrument twice.
    """
    all_results = []
    seen_ips    = set()
    for label, cidr in subnets:
        for r in scan_ethernet(cidr, label):
            if r["address"] not in seen_ips:
                seen_ips.add(r["address"])
                all_results.append(r)
    return all_results


# ══════════════════════════ USB scan ═════════════════════════════════════════

def scan_usb() -> tuple[list[dict], list[str]]:
    """
    Scan USB-TMC instruments via PyVISA.
    Returns (results, log_lines) — log is printed by caller after
    the Ethernet progress bar finishes so output is not clobbered.
    """
    log = []

    if not PYVISA_AVAILABLE:
        log.append("[USB] pyvisa not installed — USB scan skipped.")
        log.append("      Fix: pip install pyvisa pyvisa-py pyusb")
        return [], log

    rm = _open_rm()
    log.append(f"[USB] VISA backend: {rm.visalib}")

    # Collect USB resources — LeCroy IVI uses ::INST, standard VISA uses ::INSTR
    usb_resources = []
    for pattern in ("USB?*::INSTR", "USB?*::INST", "USB?*"):
        try:
            found = list(rm.list_resources(pattern))
            for r in found:
                if r not in usb_resources:
                    usb_resources.append(r)
        except Exception as exc:
            log.append(f"[USB] list_resources('{pattern}') failed: {exc}")
        if usb_resources:
            break   # stop at first pattern that yields results

    if not usb_resources:
        log.append("[USB] No USB-TMC devices detected.")
        rm.close()
        return [], log

    log.append(f"[USB] {len(usb_resources)} USB device(s) enumerated — querying IDN …")
    results = []

    for res in usb_resources:
        idn = ""
        try:
            inst = rm.open_resource(res, open_timeout=IDN_TIMEOUT * 1000)
            inst.timeout = IDN_TIMEOUT * 1000
            idn  = inst.query("*IDN?").strip()
            inst.close()
        except Exception as exc:
            log.append(f"  [USB] {res} — open/IDN failed: {exc}")
            continue
        if not idn:
            log.append(f"  [USB] {res} — no IDN response, skipped.")
            continue
        vendor = detect_vendor(idn)
        entry = {
            "type"    : "USB",
            "address" : res,
            "port"    : "USB-TMC",
            "idn"     : idn,
            "vendor"  : vendor or "Unknown",
            "resource": res,
        }
        log.append(f"  [FOUND] USB  {vendor}  {idn[:70]}")
        results.append(entry)

    rm.close()
    return results, log


# ══════════════════════════ Output ═══════════════════════════════════════════

COLUMNS = ["type", "address", "port", "vendor", "idn", "resource"]
COL_W   = [9, 17, 8, 22, 52, 42]


def _row(values: list, widths: list) -> str:
    return "  ".join(str(v).ljust(w)[:w] for v, w in zip(values, widths))


def print_results(results: list[dict]) -> None:
    if not results:
        return

    header = _row(["TYPE", "ADDRESS", "PORT", "VENDOR", "IDN", "VISA RESOURCE"], COL_W)
    sep    = "  ".join("─" * w for w in COL_W)

    print(f"\n{'═'*120}")
    print(f"  {'SCAN RESULTS':^116}")
    print(f"{'═'*120}")
    print(f"  {header}")
    print(f"  {sep}")
    for r in results:
        row = _row([r["type"], r["address"], str(r["port"]),
                    r["vendor"], r["idn"], r["resource"]], COL_W)
        print(f"  {row}")
    print(f"{'═'*120}")
    print(f"\n  Total found: {len(results)} instrument(s)")


def save_csv(results: list[dict], path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(results)
    print(f"\n  CSV saved  →  {path}")


# ══════════════════════════════ Main ═════════════════════════════════════════

def main() -> None:
    ts = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    print("=" * 60)
    print("  Oscilloscope / Instrument Scanner")
    print(f"  {ts}")
    print("=" * 60)

    if not SCAN_ETHERNET and not SCAN_USB:
        print("[ERROR] Both SCAN_ETHERNET and SCAN_USB are False — nothing to do.")
        sys.exit(1)

    results     = []
    eth_results = []
    usb_results = []
    usb_log     = []

    # ── Run Ethernet and USB scans in parallel ─────────────────────────
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {}
        if SCAN_ETHERNET:
            if SUBNET:
                subnets = [("(manual)", SUBNET)]
            else:
                subnets = get_all_subnets()
            print(f"\n  Network interfaces to scan ({len(subnets)}):")
            for label, cidr in subnets:
                print(f"    {label:<22} {cidr}")
            futures["eth"] = pool.submit(scan_all_ethernet, subnets)
        if SCAN_USB:
            futures["usb"] = pool.submit(scan_usb)

        if "eth" in futures:
            eth_results = futures["eth"].result()   # blocks until ETH done (progress bar finished)
        if "usb" in futures:
            usb_results, usb_log = futures["usb"].result()

    # ── Print USB log now (after Ethernet progress bar is gone) ────────
    if usb_log:
        print()
        for line in usb_log:
            print(line)

    results = eth_results + usb_results

    # ── Print table (only if something was found) ───────────────────────
    if results:
        print_results(results)
        if CSV_OUTPUT:
            save_csv(results, CSV_OUTPUT)
        print("\n  Tip: copy a VISA resource string above into lecroy_capture.py")
        print("       SCOPE_IP   (Ethernet)  or  USB_RESOURCE  (USB)")
    else:
        print("\n  No instruments found.")


if __name__ == "__main__":
    main()
