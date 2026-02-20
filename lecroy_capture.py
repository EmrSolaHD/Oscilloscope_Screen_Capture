"""
╔══════════════════════════════════════════════════════════════════════════╗
║          Oscilloscope Screen Capture — USB or Ethernet (SCPI)           ║
║                           Turnkey Script                                ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Works with: LeCroy, Tektronix, Keysight/Agilent, Rigol, Siglent, …   ║
║  Protocol  : SCPI over VISA (USB-TMC  or  TCP/IP VXI-11 / HiSLIP)     ║
╚══════════════════════════════════════════════════════════════════════════╝

 QUICK START
 ───────────
 1. Install dependencies once:
       pip install -r requirements.txt

 2. Edit the USER CONFIGURATION section below (8 lines).

 3. Run:
       python lecroy_capture.py

 CONNECTION TYPES
 ────────────────
  "ETHERNET"  — Scope connected via LAN/Ethernet.
                 PC and scope must share a subnet (or have a gateway route).
                 Typical VISA resource:  TCPIP::1[<This is IP address placeholder>]::inst0::INSTR

  "USB"        — Scope connected via USB-B cable (USB-TMC).
                 Set USB_RESOURCE to the exact VISA string, OR leave it ""
                 to have the script list all connected instruments and pick
                 the first one automatically.
                 Typical VISA resource:  USB0::0x05FF::0x1023::12345::INSTR

 VENDOR NOTES
 ────────────
  LeCroy / Teledyne : HCSU + SCREEN_DUMP (auto-selected)
  Tektronix          : HARDcopy START     (auto-selected)
  Keysight / Agilent : :DISP:DATA? PNG   (auto-selected)
  Rigol / Siglent    : :DISP:DATA?        (auto-selected)
  Other / Unknown    : Tries all methods in sequence
"""

# ═══════════════════════════ USER CONFIGURATION ════════════════════════════ #

# ── Connection type: "ETHERNET"  or  "USB" ──────────────────────────────── #
CONNECTION_TYPE = "ETHERNET"
CONNECTION_TYPE = "USB"

# ── Ethernet settings (used when CONNECTION_TYPE = "ETHERNET") ────────────── #
SCOPE_IP        = "1[<This is IP address placeholder>]"   # IP address of the oscilloscope
SCOPE_PORT      = 0                # 0 = auto  |  1861 = VICP  |  5025 = SCPI raw
                                   # (auto tries VXI-11 first, then HiSLIP, then raw)
USERNAME        = ""               # HTTP/web auth — leave "" if not required
PASSWORD        = ""               # HTTP/web auth — leave "" if not required

# ── USB settings (used when CONNECTION_TYPE = "USB") ──────────────────────── #
#USB_RESOURCE    = "[<This is USB address pleaceholder>]"               # e.g. "USB0::0x05FF::0x1023::12345::INSTR"
USB_RESOURCE    = "[<This is USB address placeholder>]"               # e.g. "USB0::0x05FF::0x1023::12345::INSTR"
                                   # Leave "" to auto-detect first USB instrument

# ── Output ────────────────────────────────────────────────────────────────── #
SAVE_PATH       = r"C:\captures\scope_screenshot.png"   # .png  or  .bmp
                                   # Timestamp is appended automatically:
                                   # e.g.  scope_screenshot_20260219_143055.png

# ── Timeout ───────────────────────────────────────────────────────────────── #
TIMEOUT_SEC     = 15               # Seconds to wait for TCP/USB responses
# ── Display color ────────────────────────────────────────────────────────────── #
DISPLAY_COLOR   = "WHITE"          # Background color of the captured screenshot
                                   #   "WHITE" — white background  (best for printing)
                                   #   "BLACK" — black background  (scope’s native look)
                                   # Applies to: LeCroy (BCKG), Tektronix (INKSaver),
                                   #             Keysight (SCR/INKS), Rigol/Siglent (COL)
# ═══════════════════════════════════════════════════════════════════════════ #
#  Do NOT edit below this line unless you know what you are doing.
# ═══════════════════════════════════════════════════════════════════════════ #

import os
import sys
import time
import ipaddress
import socket

# ── Pillow ────────────────────────────────────────────────────────────────
try:
    from PIL import Image
    import io as _io
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("[WARN] Pillow not installed — images saved as raw BMP.")
    print("       Install with:  pip install Pillow\n")

# ── PyVISA ────────────────────────────────────────────────────────────────
try:
    import pyvisa
except ImportError:
    print("[ERROR] pyvisa is required but not installed.")
    print("        Run:  pip install pyvisa pyvisa-py")
    sys.exit(1)

def _open_rm() -> pyvisa.ResourceManager:
    """
    Return the best available VISA ResourceManager.

    Priority:
      1. System VISA backend (NI-VISA, Keysight IO, IVI Foundation driver)
         — required to see devices that show as IVI in Windows Device Manager.
      2. pyvisa-py pure-Python backend (@py)
         — fallback when no system VISA is installed.
    """
    try:
        rm = pyvisa.ResourceManager()   # system VISA (NI / Keysight / IVI)
        rm.list_resources()             # test — raises if backend is unusable
        return rm
    except Exception:
        pass
    return pyvisa.ResourceManager("@py")

# ══════════════════════════ Path utilities ══════════════════════════════════

def _timestamped_path(base_path: str) -> str:
    r"""
    Insert a timestamp between the file stem and extension.
    e.g.  C:\captures\scope_screenshot.png
          ->  C:\captures\scope_screenshot_20260219_143055.png
    """
    from datetime import datetime
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    root, ext = os.path.splitext(base_path)
    return f"{root}_{ts}{ext}"


# ══════════════════════════ Network utilities ═══════════════════════════════

def validate_ip(ip_str: str) -> None:
    try:
        ipaddress.ip_address(ip_str)
    except ValueError:
        print(f"[ERROR] '{ip_str}' is not a valid IP address.")
        sys.exit(1)


def get_local_ip_for(remote_ip: str) -> str:
    """Return the local NIC IP that would route to *remote_ip*."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect((remote_ip, 80))
            return s.getsockname()[0]
    except Exception:
        return "unknown"


def subnet_info(scope_ip: str) -> None:
    local_ip = get_local_ip_for(scope_ip)
    print(f"  Local  NIC  : {local_ip}")
    print(f"  Scope  IP   : {scope_ip}")
    try:
        local_net  = ipaddress.IPv4Interface(f"{local_ip}/24").network
        scope_addr = ipaddress.ip_address(scope_ip)
        if scope_addr in local_net:
            print(f"  Subnet      : Same subnet ({local_net}) — direct connection OK")
        else:
            print(f"  Subnet      : Different subnet — requires gateway / static route")
            print(f"                Local /24 : {local_net}")
    except Exception:
        pass


def check_tcp_reachable(ip: str, timeout: int = 3) -> bool:
    """Try common scope ports; return True if any responds."""
    for port in (1861, 5025, 80):
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                return True
        except OSError:
            continue
    return False


# ══════════════════════════ VISA resource helpers ═══════════════════════════

def build_ethernet_resources(ip: str, port: int) -> list:
    """
    Return VISA resource strings to try in order.
    VXI-11 (inst0) and HiSLIP (hislip0) are the two standard LAN protocols.
    A raw SOCKET resource is also included as last-resort fallback.
    """
    resources = []
    if port in (0, 1861, 5025):
        resources += [
            f"TCPIP::{ip}::inst0::INSTR",    # VXI-11
            f"TCPIP::{ip}::hislip0::INSTR",  # HiSLIP (newer scopes)
        ]
        p = 5025 if port in (0, 5025) else 1861
        resources.append(f"TCPIP::{ip}::{p}::SOCKET")  # raw SCPI socket
    else:
        resources = [
            f"TCPIP::{ip}::inst0::INSTR",
            f"TCPIP::{ip}::hislip0::INSTR",
            f"TCPIP::{ip}::{port}::SOCKET",
        ]
    return resources


def find_usb_resource(rm: pyvisa.ResourceManager) -> str | None:
    """
    Return the VISA resource string of the first USB instrument found.
    Searches for both ::INSTR (standard) and ::INST (LeCroy IVI driver).
    """
    resources = []
    for pattern in ("USB?*::INSTR", "USB?*::INST", "USB?*"):
        try:
            found = list(rm.list_resources(pattern))
            # de-duplicate while preserving order
            for r in found:
                if r not in resources:
                    resources.append(r)
        except Exception:
            pass
        if resources:
            break   # stop at the first pattern that yields results

    if not resources:
        print("[USB] No USB instruments found by VISA.")
        print("      Check: cable, IVI/NI-VISA driver, and USB cable.")
        return None

    print(f"[USB] Found {len(resources)} USB instrument(s):")
    for i, r in enumerate(resources):
        print(f"      [{i}] {r}")
    return resources[0]


# ══════════════════════════ Vendor detection ════════════════════════════════

def detect_vendor(idn: str) -> str:
    """
    Parse *IDN? response and return a short vendor tag.
    Format: <manufacturer>,<model>,<serial>,<firmware>
    """
    idn_upper = idn.upper()
    if "LECROY" in idn_upper or "TELEDYNE" in idn_upper:
        return "LECROY"
    if "TEKTRONIX" in idn_upper or "TEK" in idn_upper:
        return "TEKTRONIX"
    if "KEYSIGHT" in idn_upper or "AGILENT" in idn_upper or "HEWLETT" in idn_upper:
        return "KEYSIGHT"
    if "RIGOL" in idn_upper:
        return "RIGOL"
    if "SIGLENT" in idn_upper:
        return "SIGLENT"
    if "ROHDE" in idn_upper or "ROHDE&SCHWARZ" in idn_upper or "R&S" in idn_upper:
        return "RNS"
    return "UNKNOWN"


# ══════════════════════════ SCPI screen capture ═════════════════════════════

def scpi_capture(resource_str: str, save_path: str, timeout_ms: int) -> bool:
    """
    Open *resource_str* via VISA, identify the instrument, issue the
    appropriate SCPI screen-dump command, receive the binary image, and
    save it to *save_path*.

    Returns True on success, False on any failure.
    """
    rm = _open_rm()   # system VISA (NI/IVI) preferred; falls back to pyvisa-py

    print(f"\n[VISA] Opening: {resource_str}")

    # LeCroy IVI driver uses ::INST; standard VISA uses ::INSTR.
    # Build a list of variants to try so either suffix works.
    candidates = [resource_str]
    if resource_str.endswith("::INSTR"):
        candidates.append(resource_str[:-len("INSTR")] + "INST")
    elif resource_str.endswith("::INST"):
        candidates.append(resource_str[:-len("INST")] + "INSTR")

    scope = None
    for attempt in candidates:
        try:
            scope = rm.open_resource(attempt, open_timeout=timeout_ms)
            if attempt != resource_str:
                print(f"[VISA] Opened with adjusted suffix: {attempt}")
            break
        except pyvisa.errors.VisaIOError:
            scope = None

    if scope is None:
        print(f"[VISA] Cannot open resource (tried: {candidates})")
        rm.close()
        return False

    try:
        scope.timeout = timeout_ms

        # ── Set termination for text queries ──────────────────────────────
        scope.read_termination  = "\n"
        scope.write_termination = "\n"

        # ── Identify instrument ───────────────────────────────────────────
        try:
            idn = scope.query("*IDN?").strip()
        except Exception:
            idn = "(no IDN response)"
        vendor = detect_vendor(idn)
        print(f"[VISA] Instrument : {idn}")
        print(f"[VISA] Vendor tag : {vendor}")

        # ── Issue screen-dump SCPI command(s) by vendor ───────────────────
        image_data = _screen_dump(scope, vendor)

        if not image_data or len(image_data) < 100:
            print(f"[VISA] Image data too small ({len(image_data) if image_data else 0} bytes).")
            # ── LeCroy Ethernet fallback: VXI-11 can’t carry the binary image;
            #    retry with raw VICP socket directly on port 1861.
            if vendor == "LECROY" and "TCPIP::" in resource_str.upper():
                ip = resource_str.split("::")[1]
                color = DISPLAY_COLOR.upper() if DISPLAY_COLOR.upper() in ("WHITE","BLACK") else "WHITE"
                print(f"[VICP] VXI-11 image transfer failed — falling back to raw VICP on {ip}:1861")
                try:
                    scope.close()
                except Exception:
                    pass
                rm.close()
                try:
                    image_data = _dump_lecroy_vicp_raw(ip, color, timeout_ms // 1000)
                except Exception as exc:
                    print(f"[VICP] Raw VICP also failed: {exc}")
                    return False
                if not image_data or len(image_data) < 100:
                    print(f"[VICP] Raw VICP returned too little data ({len(image_data) if image_data else 0} bytes).")
                    return False
                image_data = _strip_ieee_block(image_data)
                _save_image(image_data, save_path)
                return True
            return False

        image_data = _strip_ieee_block(image_data)
        _save_image(image_data, save_path)
        return True

    except Exception as exc:
        print(f"[VISA] Error: {exc}")
        return False
    finally:
        try:
            scope.close()
        except Exception:
            pass
        rm.close()


def _screen_dump(scope, vendor: str) -> bytes | None:
    """
    Dispatch to the correct vendor SCPI command set and return raw image bytes.
    Falls back to generic methods if vendor is unknown.
    """
    color = DISPLAY_COLOR.upper()
    if color not in ("WHITE", "BLACK"):
        print(f"[WARN] Unknown DISPLAY_COLOR '{DISPLAY_COLOR}' — defaulting to WHITE.")
        color = "WHITE"

    if vendor == "LECROY":
        return _dump_lecroy(scope, color)
    if vendor == "TEKTRONIX":
        return _dump_tektronix(scope, color)
    if vendor in ("KEYSIGHT", "AGILENT"):
        return _dump_keysight(scope, color)
    if vendor in ("RIGOL", "SIGLENT"):
        return _dump_rigol(scope, color)

    # Unknown vendor — try methods in order
    print("[SCPI] Unknown vendor — trying all capture methods …")
    for fn in (_dump_keysight, _dump_rigol, _dump_lecroy, _dump_tektronix):
        try:
            data = fn(scope, color)
            if data and len(data) > 100:
                return data
        except Exception:
            continue
    return None


# ── Vendor-specific SCPI capture implementations ─────────────────────────

# VICP constants (LeCroy Visual Instrument Control Protocol, port 1861)
_VICP_HDR   = ">BBBBI"    # op(1) ver(1) seq(1) pad(1) len(4)
_VICP_HLEN  = 8
_VICP_SEQ   = [0]

def _vicp_next_seq() -> int:
    _VICP_SEQ[0] = (_VICP_SEQ[0] % 255) + 1
    return _VICP_SEQ[0]

def _vicp_send(sock: socket.socket, cmd: str) -> None:
    import struct
    payload = cmd.encode("ascii")
    op      = 0x80 | 0x40 | 0x01   # DATA | REMOTE | EOI
    hdr     = struct.pack(_VICP_HDR, op, 0x01, _vicp_next_seq(), 0x00, len(payload))
    sock.sendall(hdr + payload)

def _vicp_recv(sock: socket.socket) -> bytes:
    """
    Read one or more VICP frames until the EOI flag (bit 0 of op) is set
    OR the scope closes the connection / the socket times out (both are
    treated as a valid end-of-data condition for LeCroy).

    Op-byte flags:  DATA=0x80  REMOTE=0x40  LOCKOUT=0x20  CLEAR=0x10
                    SRQ=0x08   REQSEND=0x04  EOI=0x01
    Only frames with DATA set contribute to the image payload; any other
    frames (SRQ, etc.) are consumed and discarded.
    """
    import struct

    def recv_exact(n: int) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError(f"VICP: remote closed after {len(buf)}/{n} bytes.")
            buf.extend(chunk)
        return bytes(buf)

    image   = bytearray()
    frame_n = 0
    try:
        while True:
            raw_hdr = recv_exact(_VICP_HLEN)
            op, _, _, _, length = struct.unpack(_VICP_HDR, raw_hdr)
            is_data = bool(op & 0x80)   # DATA bit
            eoi     = bool(op & 0x01)   # EOI  bit — last frame of message
            if length:
                payload = recv_exact(length)
                if is_data:
                    image.extend(payload)
                # silently discard SRQ / control frames
            frame_n += 1
            print(f"[VICP]   frame {frame_n:3d}: op=0x{op:02X}  len={length:,}  "
                  f"total={len(image):,}  eoi={eoi}", flush=True)
            if eoi:
                break
    except (ConnectionError, OSError):
        # scope closed the TCP connection — treat accumulated data as complete
        print(f"[VICP] Connection closed by scope after {frame_n} frame(s) — "
              f"{len(image):,} bytes total.", flush=True)
    except Exception as exc:  # socket.timeout or anything else
        print(f"[VICP] Receive ended ({exc}) after {frame_n} frame(s) — "
              f"{len(image):,} bytes total.", flush=True)
    return bytes(image)


def _dump_lecroy_vicp_raw(ip: str, color: str, timeout_sec: int) -> bytes:
    """
    Capture LeCroy screen directly via raw VICP TCP socket on port 1861.
    This bypasses pyvisa/VXI-11 entirely — required because LeCroy sends
    the binary image data only over VICP, not VXI-11.
    """
    print(f"[VICP] Connecting directly to {ip}:1861 (raw VICP) …")
    sock = socket.create_connection((ip, 1861), timeout=timeout_sec)
    sock.settimeout(timeout_sec)
    try:
        _vicp_send(sock, f"HCSU DEV,BMP,FORMAT,PORTRAIT,BCKG,{color},DEST,REMOTE,PORT,NET")
        time.sleep(0.5)
        _vicp_send(sock, "SCREEN_DUMP")
        time.sleep(4.0)   # allow scope time to render full BMP before first frame arrives
        data = _vicp_recv(sock)
    finally:
        sock.close()
    return data


def vicp_capture(ip: str, save_path: str, timeout_sec: int) -> bool:
    """
    Full LeCroy capture path using raw VICP on port 1861 — no VISA / VXI-11.
    Sends *IDN? first to confirm the target is a LeCroy scope, then sends
    HCSU + SCREEN_DUMP and receives the BMP image in one or more VICP frames.
    Returns True on success, False on any failure.
    """
    color = DISPLAY_COLOR.upper() if DISPLAY_COLOR.upper() in ("WHITE", "BLACK") else "WHITE"

    print(f"[VICP] Trying native VICP on {ip}:1861 …")
    try:
        sock = socket.create_connection((ip, 1861), timeout=timeout_sec)
        sock.settimeout(timeout_sec)
    except OSError as exc:
        print(f"[VICP] Cannot connect to {ip}:1861 — {exc}")
        return False

    try:
        # ── Step 1: identify instrument ───────────────────────────────────
        _vicp_send(sock, "*IDN?")
        time.sleep(0.2)
        idn_raw = _vicp_recv(sock)
        idn     = idn_raw.decode("ascii", errors="replace").strip()
        vendor  = detect_vendor(idn)
        print(f"[VICP] Instrument : {idn}")
        print(f"[VICP] Vendor tag : {vendor}")

        if vendor != "LECROY":
            print(f"[VICP] Not a LeCroy — skipping VICP path.")
            return False

        # ── Step 2: configure and trigger screen dump ─────────────────────
        _vicp_send(sock, f"HCSU DEV,BMP,FORMAT,PORTRAIT,BCKG,{color},DEST,REMOTE,PORT,NET")
        time.sleep(0.5)
        _vicp_send(sock, "SCREEN_DUMP")
        time.sleep(4.0)   # scope needs time to render full BMP

        # ── Step 3: receive multi-frame VICP image response ───────────────
        image_data = _vicp_recv(sock)

    except Exception as exc:
        print(f"[VICP] Error during capture: {exc}")
        return False
    finally:
        sock.close()

    if not image_data or len(image_data) < 100:
        print(f"[VICP] Image data too small ({len(image_data) if image_data else 0} bytes).")
        return False

    image_data = _strip_ieee_block(image_data)
    _save_image(image_data, save_path)
    return True


def _dump_lecroy(scope, color: str = "WHITE") -> bytes:
    """
    LeCroy / Teledyne LeCroy.
    HCSU configures hardcopy: BMP, background color, send to remote (bus).
    SCREEN_DUMP triggers the transfer.
    color: "WHITE" or "BLACK"
    """
    scope.write(f"HCSU DEV,BMP,FORMAT,PORTRAIT,BCKG,{color},DEST,REMOTE,PORT,NET")
    time.sleep(0.3)
    scope.write("SCREEN_DUMP")
    time.sleep(1.5)
    scope.read_termination = None        # binary transfer — no text terminator
    data = scope.read_raw()
    return data


def _dump_tektronix(scope, color: str = "WHITE") -> bytes:
    """
    Tektronix TDS / MDO / MSO / DPO series.
    HARDcopy START sends image data on the bus.
    INKSaver ON  = white background; OFF = black (native) background.
    color: "WHITE" -> INKSaver ON  |  "BLACK" -> INKSaver OFF
    """
    ink = "ON" if color == "WHITE" else "OFF"
    scope.write("HARDcopy:PORT GPIB")   # route output to bus
    scope.write("HARDcopy:FORMat BMP")
    scope.write(f"HARDcopy:INKSaver {ink}")
    time.sleep(0.2)
    scope.write("HARDcopy START")
    time.sleep(2.0)
    scope.read_termination = None
    data = scope.read_raw()
    return data


def _dump_keysight(scope, color: str = "WHITE") -> bytes:
    """
    Keysight / Agilent InfiniiVision, Infiniium series.
    :DISP:DATA? returns a definite-length binary block with a PNG image.
    COL  = color display  |  GRAY = grayscale
    SCR  = screen colors (black bg)  |  INKS = ink-saver (white bg)
    color: "WHITE" -> INKS  |  "BLACK" -> SCR
    """
    scheme = "INKS" if color == "WHITE" else "SCR"
    scope.write(f":DISP:DATA PNG,{scheme},COL")   # some older models omit args
    time.sleep(0.5)
    scope.read_termination = None
    data = scope.query_binary_values(
        f":DISP:DATA? PNG,{scheme},COL",
        datatype="B",
        container=bytes,
        delay=0.5,
    )
    return bytes(data) if data else b""


def _dump_rigol(scope, color: str = "WHITE") -> bytes:
    """
    Rigol DS / MSO series and Siglent SDS series.
    :DISP:DATA? returns a PNG block.
    ON = normal screen colors (black bg)  |  OFF = inverted/white bg
    color: "WHITE" -> invert OFF  |  "BLACK" -> invert ON (native)
    """
    # Rigol: :DISP:GBColor sets grid/background; no direct invert on all models.
    # Best available: send color hint via the query argument where supported.
    arg = "OFF" if color == "WHITE" else "ON"
    scope.write(f":DISP:DATA? ON,{arg},PNG")
    time.sleep(0.5)
    scope.read_termination = None
    data = scope.read_raw()
    if not data or len(data) < 10:
        # Fallback: plain query without color args (older firmware)
        scope.write(":DISP:DATA?")
        time.sleep(0.5)
        data = scope.read_raw()
    return data


# ══════════════════════════ Image utilities ══════════════════════════════════

def _strip_ieee_block(data: bytes) -> bytes:
    """Remove IEEE 488.2 definite-length block header  #N<N digits><data>."""
    if data and data[0:1] == b"#":
        try:
            n_digits  = int(chr(data[1]))
            byte_count = int(data[2 : 2 + n_digits])
            data       = data[2 + n_digits : 2 + n_digits + byte_count]
        except Exception:
            pass
    return data


def _save_image(image_data: bytes, save_path: str) -> None:
    out_dir = os.path.dirname(os.path.abspath(save_path))
    os.makedirs(out_dir, exist_ok=True)

    if PILLOW_AVAILABLE:
        try:
            img = Image.open(_io.BytesIO(image_data))
            img.save(save_path)
            print(f"\n{'='*60}")
            print(f"  Screenshot saved  →  {save_path}")
            print(f"  Dimensions        :  {img.size[0]} × {img.size[1]} px")
            print(f"  File size         :  {os.path.getsize(save_path):,} bytes")
            print(f"{'='*60}")
            return
        except Exception as exc:
            print(f"[WARN] Pillow decode failed ({exc}) — saving raw bytes.")

    ext      = os.path.splitext(save_path)[1].lower()
    raw_path = save_path if ext == ".bmp" else os.path.splitext(save_path)[0] + ".bmp"
    with open(raw_path, "wb") as fh:
        fh.write(image_data)
    print(f"\n[OK] Raw image saved  →  {raw_path}  ({len(image_data):,} bytes)")


# ══════════════════════════ HTTP auth helper ════════════════════════════════

def try_http_auth(ip: str, user: str, pwd: str, timeout: int) -> None:
    """
    Some LeCroy / Keysight scopes gate their LAN interface behind an HTTP
    Basic Auth challenge on port 80.  This performs the handshake silently.
    """
    try:
        import urllib.request, base64
        req = urllib.request.Request(f"http://{ip}/")
        if user:
            creds = base64.b64encode(f"{user}:{pwd}".encode()).decode()
            req.add_header("Authorization", f"Basic {creds}")
        urllib.request.urlopen(req, timeout=timeout)
        print("[AUTH] HTTP authentication handshake succeeded.")
    except Exception:
        pass  # non-fatal — most scopes don't require this


# ══════════════════════════════ Main ════════════════════════════════════════

def main() -> None:

    print("=" * 60)
    print("  Oscilloscope Screen Capture  (SCPI / VISA)")
    print("=" * 60)
    print(f"  Connection  : {CONNECTION_TYPE}")

    # Build the actual output path with timestamp appended
    save_path  = _timestamped_path(SAVE_PATH)
    print(f"  Output      : {save_path}")

    timeout_ms = TIMEOUT_SEC * 1000

    # ────────────────────────── USB path ──────────────────────────────────
    if CONNECTION_TYPE.upper() == "USB":
        print("=" * 60)

        rm_probe = _open_rm()
        resource = USB_RESOURCE if USB_RESOURCE else find_usb_resource(rm_probe)
        rm_probe.close()

        if not resource:
            print("\n[FAIL] No USB resource available.")
            print("       Connect the USB cable and re-run, or set USB_RESOURCE manually.")
            sys.exit(1)

        print(f"\n[USB] Using resource: {resource}")
        success = scpi_capture(resource, save_path, timeout_ms)

    # ────────────────────────── Ethernet path ─────────────────────────────
    elif CONNECTION_TYPE.upper() == "ETHERNET":
        validate_ip(SCOPE_IP)
        subnet_info(SCOPE_IP)
        print("=" * 60)

        # HTTP auth handshake (harmless if not required)
        if USERNAME or PASSWORD:
            try_http_auth(SCOPE_IP, USERNAME, PASSWORD, TIMEOUT_SEC)

        # TCP reachability check
        print("\n[NET] Checking TCP/IP reachability …", end=" ", flush=True)
        reachable = check_tcp_reachable(SCOPE_IP, timeout=3)
        print("REACHABLE" if reachable else "NO RESPONSE")
        if not reachable:
            print("      Scope may still respond to VISA — continuing …")

        # Try native VICP first (LeCroy scopes configured in TCPIP/VICP mode)
        success = vicp_capture(SCOPE_IP, save_path, TIMEOUT_SEC)

        # Fall back to VISA resource strings (VXI-11, HiSLIP, raw socket)
        if not success:
            candidates = build_ethernet_resources(SCOPE_IP, SCOPE_PORT)
            for res in candidates:
                success = scpi_capture(res, save_path, timeout_ms)
                if success:
                    break

    else:
        print(f"\n[ERROR] Unknown CONNECTION_TYPE '{CONNECTION_TYPE}'.")
        print("        Set it to 'ETHERNET' or 'USB'.")
        sys.exit(1)

    # ────────────────────────── Result ────────────────────────────────────
    if not success:
        print("\n[FAIL] Screenshot could not be captured.")
        print("\n  Troubleshooting:")
        if CONNECTION_TYPE.upper() == "ETHERNET":
            print(f"    • Ping {SCOPE_IP} from this PC to verify connectivity.")
            print(f"    • Confirm PC and scope are on the same subnet or have a route.")
            print(f"    • On the scope: Utilities → Remote → Network ON.")
            print(f"    • Try SCOPE_PORT = 0 to auto-detect the protocol port.")
            print(f"    • Check Windows Firewall is not blocking ports 1861 / 5025.")
        else:
            print(f"    • Check the USB cable and USB-B port on the scope.")
            print(f"    • Install libusb (required by pyvisa-py for USB-TMC).")
            print(f"    • Run:  python -m visa info  to list detected resources.")
            print(f"    • Set USB_RESOURCE manually to the exact VISA string.")
        sys.exit(1)


if __name__ == "__main__":
    main()
