# LecroySS — Oscilloscope Screen Capture

> **v1.0 · Python 3.10+**  
> Multi-vendor oscilloscope screen-capture toolkit — VICP, VXI-11, HiSLIP, USB-TMC

**LecroySS** is a turnkey, zero-configuration Python toolkit for capturing screenshots from laboratory oscilloscopes over Ethernet (TCP/IP) or USB. It supports every major oscilloscope vendor through automatic vendor detection and SCPI command dispatch. For LeCroy scopes specifically, it implements the proprietary **VICP (Visual Instrument Control Protocol)** natively — bypassing the VXI-11 limitation that causes image data to arrive as a 52-byte stub.

The companion **`scope_scanner.py`** discovers all instruments on your network and USB bus simultaneously, printing a formatted results table with VISA resource strings ready to paste directly into the capture script.

| Scripts | Protocols | Vendors Supported | Python |
|---------|-----------|-------------------|--------|
| 2 | 4 | 5+ | 3.10+ |
| `lecroy_capture.py` · `scope_scanner.py` | VICP · VXI-11 · HiSLIP · USB-TMC | LeCroy · Tektronix · Keysight · Rigol · Siglent | Uses modern type hints and match expressions |

---

## Table of Contents

- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Configuration Reference](#configuration-reference)
- [Ethernet Capture Flow](#ethernet-capture-flow)
- [USB Capture Flow](#usb-capture-flow)
- [VICP Protocol](#vicp-protocol)
- [VISA / VXI-11 Fallback](#visa--vxi-11-fallback)
- [Vendor Detection & Dispatch](#vendor-detection--dispatch)
- [Image Utilities](#image-utilities)
- [Network Utilities](#network-utilities)
- [API Reference — lecroy_capture.py](#api-reference--lecroy_capturepy)
- [scope_scanner.py](#scope_scannerpy)
- [Protocol Reference](#protocol-reference)
- [Vendor SCPI Commands](#vendor-scpi-commands)
- [Dependencies](#dependencies)
- [Troubleshooting](#troubleshooting)

---

## Architecture

Both scripts are deliberately **single-file, dependency-minimal**. All configuration lives at the top of each file in a clearly-delimited `USER CONFIGURATION` block so operators can use the tools without reading the source code.

### Module Layers — `lecroy_capture.py`

| Layer | Functions / Constants | Responsibility |
|---|---|---|
| Config | Top 80 lines | User-editable settings: IP, USB resource, save path, timeout, color |
| VISA helpers | `_open_rm()` | NI-VISA / IVI system backend with pyvisa-py fallback |
| Path utilities | `_timestamped_path()` | Insert `_YYYYMMDD_HHMMSS` before file extension |
| Network utilities | `validate_ip()`, `subnet_info()`, `check_tcp_reachable()`, `get_local_ip_for()` | IP validation, subnet comparison, reachability probe |
| VISA resource builder | `build_ethernet_resources()`, `find_usb_resource()` | Construct candidate VISA strings; enumerate USB devices |
| Vendor detection | `detect_vendor()` | Parse `*IDN?` response into short tag |
| VICP protocol | `_vicp_send()`, `_vicp_recv()`, `_dump_lecroy_vicp_raw()`, `vicp_capture()` | Full LeCroy VICP native path over port 1861 |
| SCPI capture | `scpi_capture()`, `_screen_dump()` | VISA open → IDN → vendor dispatch → image receive |
| Vendor implementations | `_dump_lecroy()`, `_dump_tektronix()`, `_dump_keysight()`, `_dump_rigol()` | Vendor-specific SCPI hardcopy commands |
| Image utilities | `_strip_ieee_block()`, `_save_image()` | IEEE 488.2 block header removal; PNG/BMP save with Pillow |
| Auth helper | `try_http_auth()` | HTTP Basic Auth handshake for web-gated scope interfaces |
| Entry point | `main()` | Top-level orchestration; USB / Ethernet branching |

---

## Quick Start

### 1 · Install dependencies

```bat
REM One-shot setup (Windows)
setup.bat

REM Manual equivalent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2 · Edit configuration

```python
# ── Connection type ──────────────────────────────────────── #
CONNECTION_TYPE = "ETHERNET"   # or "USB"

# ── Ethernet ─────────────────────────────────────────────── #
SCOPE_IP        = "1[<This is IP address placeholder>]"
SCOPE_PORT      = 0            # 0 = auto

# ── USB ──────────────────────────────────────────────────── #
USB_RESOURCE    = ""           # "" = auto-detect

# ── Output ───────────────────────────────────────────────── #
SAVE_PATH       = r"C:\captures\scope_screenshot.png"
DISPLAY_COLOR   = "WHITE"      # "WHITE" or "BLACK"
```

### 3 · Run

```bash
python lecroy_capture.py

# Discover instruments first
python scope_scanner.py
```

---

## Configuration Reference

| Variable | Type | Default | Description |
|---|---|---|---|
| `CONNECTION_TYPE` | str | `"ETHERNET"` | Connection mode. `"ETHERNET"` or `"USB"`. |
| `SCOPE_IP` | str | `"1[<This is IP address placeholder>]"` | IPv4 address of the oscilloscope. Ethernet mode only. |
| `SCOPE_PORT` | int | `0` | `0` = auto (tries VXI-11 → HiSLIP → raw SCPI). Set `1861` for VICP-only, `5025` for raw SCPI-only. |
| `USERNAME` | str | `""` | HTTP Basic Auth username. Required only if the scope web interface is password-protected. |
| `PASSWORD` | str | `""` | HTTP Basic Auth password. Leave empty if not used. |
| `USB_RESOURCE` | str | `""` | Exact VISA resource string for USB, e.g. `"[<This is USB address placeholder>]"`. Leave `""` to auto-detect. |
| `SAVE_PATH` | str | `r"C:\captures\scope_screenshot.png"` | Output file path. Accepts `.png` or `.bmp`. Timestamp is appended automatically before the extension. |
| `TIMEOUT_SEC` | int | `15` | Global timeout in seconds for TCP connections and VISA operations. |
| `DISPLAY_COLOR` | str | `"WHITE"` | Screenshot background: `"WHITE"` (print-friendly) or `"BLACK"` (scope native look). |

---

## Ethernet Capture Flow

When `CONNECTION_TYPE = "ETHERNET"`, the script follows a strict priority-ordered protocol cascade. VICP is always tried first because LeCroy scopes in *TCPIP/VICP mode* cannot transfer binary image data over VXI-11.

1. **Validate & diagnose** — `validate_ip()` checks the IP string format. `subnet_info()` detects the local NIC and prints whether scope and PC share the same /24 subnet. `check_tcp_reachable()` probes ports 1861, 5025, 80.

2. **`vicp_capture()` — Native VICP on port 1861** — Opens a raw TCP socket to port 1861. Sends `*IDN?` as a VICP frame, confirms vendor == LECROY. Then sends `HCSU` + `SCREEN_DUMP` and accumulates all multi-frame VICP response data. Returns `True` on a successful >100-byte image.

3. **`scpi_capture()` — VISA / VXI-11 (fallback)** — Only reached if VICP fails (non-LeCroy scope, or VICP disabled). Tries VISA resource strings in order: `inst0::INSTR` (VXI-11) → `hislip0::INSTR` (HiSLIP) → `5025::SOCKET` (raw SCPI).

4. **VICP socket fallback inside `scpi_capture()`** — If VXI-11 opens successfully but the image is too small (<100 bytes) and the vendor is LECROY, the function closes the VISA connection and retries via `_dump_lecroy_vicp_raw()`.

---

## USB Capture Flow

1. **Open ResourceManager** — `_open_rm()` tries the system VISA backend first (NI-VISA, Keysight IO, IVI Foundation). If the system backend raises, falls back to `pyvisa.ResourceManager("@py")` (pure Python, requires `pyusb` + `libusb`).

2. **Resolve USB resource string** — If `USB_RESOURCE` is set, it is used directly. Otherwise `find_usb_resource()` searches three VISA glob patterns: `USB?*::INSTR` → `USB?*::INST` → `USB?*`, stopping at the first match. This covers both standard USB-TMC (`::INSTR`) and LeCroy IVI driver suffix (`::INST`).

3. **`scpi_capture()` with suffix retry** — If the resource string ends in `::INSTR`, a variant with `::INST` is also added to the candidate list (and vice versa). This silently corrects LeCroy IVI driver suffix mismatches without requiring the user to know the exact suffix.

---

## VICP Protocol

**VICP (Visual Instrument Control Protocol)** is LeCroy's proprietary TCP/IP instrument control protocol. It runs on **port 1861** and predates VXI-11. Every message is prefixed with an 8-byte binary header.

### Frame Structure

| Byte 0 | Byte 1 | Byte 2 | Byte 3 | Bytes 4–7 | Bytes 8… |
|--------|--------|--------|--------|-----------|----------|
| OP (flags) | VER (`0x01`) | SEQ (1–255) | PAD (`0x00`) | LEN (big-endian uint32) | PAYLOAD (ASCII cmd or binary image) |

### Operation Flags (OP byte)

| Bit | Mask | Name | Meaning |
|-----|------|------|---------|
| 7 | `0x80` | DATA | Frame carries instrument data. Frames without this bit are control/SRQ frames and should be discarded. |
| 6 | `0x40` | REMOTE | Scope should enter remote mode. |
| 5 | `0x20` | LOCKOUT | Full lockout of front panel. |
| 4 | `0x10` | CLEAR | Device clear — abort pending operations. |
| 3 | `0x08` | SRQ | Service Request (scope-to-host only). |
| 2 | `0x04` | REQSEND | Request scope to send its output buffer. |
| 0 | `0x01` | EOI | End Of Identity — last frame of the current message. Critical for detecting end of multi-frame image transfer. |

> **Why 52 bytes over VXI-11?**  
> When `SCREEN_DUMP` is sent via VXI-11 (port 111 / Sun RPC), LeCroy returns a short text acknowledgment (~52 bytes) over VXI-11 and streams the actual BMP image data separately over the VICP port (1861). If the VXI-11 client closes before listening on 1861, the image is lost. The solution is to use VICP exclusively.

> ⚠️ **Multi-frame accumulation is critical.** A WS4034HD BMP screenshot is ~3.5 MB. LeCroy splits this across many VICP frames (each up to 65,536 bytes). The receive loop must continue until the **EOI flag (bit 0)** is set on an incoming frame's OP byte, or until the socket closes.

### Python Implementation

```python
# Header format: big-endian — op(1) version(1) seq(1) pad(1) length(4)
_VICP_HDR  = ">BBBBI"
_VICP_HLEN = 8
_VICP_SEQ  = [0]   # mutable list so _vicp_next_seq() can update it

def _vicp_send(sock: socket.socket, cmd: str) -> None:
    payload = cmd.encode("ascii")
    op      = 0x80 | 0x40 | 0x01   # DATA | REMOTE | EOI
    hdr     = struct.pack(_VICP_HDR, op, 0x01, _vicp_next_seq(), 0x00, len(payload))
    sock.sendall(hdr + payload)

def vicp_capture(ip: str, save_path: str, timeout_sec: int) -> bool:
    """Full LeCroy capture — no VISA / VXI-11 required."""
    sock = socket.create_connection((ip, 1861), timeout=timeout_sec)
    _vicp_send(sock, "*IDN?")
    idn    = _vicp_recv(sock).decode("ascii").strip()
    vendor = detect_vendor(idn)
    if vendor != "LECROY": return False

    _vicp_send(sock, f"HCSU DEV,BMP,FORMAT,PORTRAIT,BCKG,{color},DEST,REMOTE,PORT,NET")
    _vicp_send(sock, "SCREEN_DUMP")
    time.sleep(4.0)   # scope renders BMP internally before sending frames

    image_data = _vicp_recv(sock)
    image_data = _strip_ieee_block(image_data)
    _save_image(image_data, save_path)
    return True
```

---

## VISA / VXI-11 Fallback

`scpi_capture()` handles all non-LeCroy instruments (Tektronix, Keysight, Rigol, Siglent) and LeCroy scopes configured with standard VXI-11 or HiSLIP.

### `_open_rm()` — Backend Selection

```python
def _open_rm() -> pyvisa.ResourceManager:
    try:
        rm = pyvisa.ResourceManager()   # NI-VISA / Keysight IO / IVI Foundation
        rm.list_resources()              # quick smoke test — raises if unusable
        return rm
    except Exception:
        pass
    return pyvisa.ResourceManager("@py")  # pyvisa-py pure Python fallback
```

> **Why prefer system VISA?** LeCroy scopes appear as *IVI devices* in Windows Device Manager when the LeCroy USB driver is installed. These devices are only visible to the NI-VISA / IVI system backend. pyvisa-py uses libusb/pyusb which enumerates USB-TMC class devices — a separate device class that LeCroy does not use.

---

## Vendor Detection & Dispatch

`detect_vendor()` parses the `*IDN?` response and returns a normalized short tag. `_screen_dump()` uses this tag to call the correct vendor-specific implementation.

```python
def detect_vendor(idn: str) -> str:
    idn_upper = idn.upper()
    if "LECROY"    in idn_upper or "TELEDYNE"  in idn_upper: return "LECROY"
    if "TEKTRONIX" in idn_upper or "TEK"       in idn_upper: return "TEKTRONIX"
    if "KEYSIGHT"  in idn_upper or "AGILENT"   in idn_upper: return "KEYSIGHT"
    if "RIGOL"     in idn_upper:                              return "RIGOL"
    if "SIGLENT"   in idn_upper:                              return "SIGLENT"
    return "UNKNOWN"
```

| Vendor | Command | Format | Color Control |
|--------|---------|--------|---------------|
| 🔬 LeCroy / Teledyne | `HCSU` + `SCREEN_DUMP` | BMP | `BCKG,WHITE` / `BCKG,BLACK` |
| 📟 Tektronix | `HARDcopy START` | BMP | INKSaver ON=white / OFF=black |
| 📏 Keysight / Agilent | `:DISP:DATA? PNG,…` | PNG (IEEE block) | INKS=white / SCR=black |
| 📡 Rigol / Siglent | `:DISP:DATA?` | PNG (IEEE block) | Limited firmware support |

---

## Image Utilities

### `_strip_ieee_block()`

The IEEE 488.2 standard defines a **definite-length arbitrary block** format: `#N<N digits of length><data>`. For example `#6065536<65536 bytes of BMP>` means 6 digits follow, the number is 065536, and then 65536 bytes of payload. The function strips this header so the caller receives clean BMP/PNG bytes.

```python
def _strip_ieee_block(data: bytes) -> bytes:
    if data and data[0:1] == b"#":
        try:
            n_digits   = int(chr(data[1]))
            byte_count = int(data[2 : 2 + n_digits])
            data       = data[2 + n_digits : 2 + n_digits + byte_count]
        except Exception:
            pass   # malformed header — return original bytes unchanged
    return data
```

### `_save_image()`

Attempts to open and re-save with Pillow first (enabling format conversion BMP→PNG and dimension printing). If Pillow fails to decode, it falls back to writing raw bytes as a `.bmp` file.

---

## Network Utilities

| Function | Description |
|---|---|
| `validate_ip(ip)` | Calls `ipaddress.ip_address()`; exits with error message on invalid string. |
| `get_local_ip_for(remote)` | Opens a UDP socket toward the remote IP and reads back the kernel-selected local IP. |
| `subnet_info(scope_ip)` | Calls `get_local_ip_for()`, builds a /24 network, checks if scope IP falls within it. |
| `check_tcp_reachable(ip)` | Tries `create_connection()` on ports 1861, 5025, and 80 in sequence. 3 s timeout per port. |
| `try_http_auth(ip, user, pwd)` | Performs HTTP Basic Auth GET to `http://<ip>/`. Only called when `USERNAME` or `PASSWORD` is non-empty. |

---

## API Reference — `lecroy_capture.py`

| Function | Signature | Returns | Notes |
|---|---|---|---|
| `_open_rm` | `() → ResourceManager` | ResourceManager | System VISA preferred, pyvisa-py fallback. |
| `_timestamped_path` | `(base: str) → str` | str | Inserts `_YYYYMMDD_HHMMSS` before extension. |
| `validate_ip` | `(ip: str) → None` | — | Calls `sys.exit(1)` on invalid IP. |
| `get_local_ip_for` | `(remote: str) → str` | str | UDP routing trick to find active NIC IP. |
| `subnet_info` | `(scope_ip: str) → None` | — | Prints NIC/scope IPs and subnet match status. |
| `check_tcp_reachable` | `(ip: str, timeout: int) → bool` | bool | Probes ports 1861, 5025, 80. |
| `build_ethernet_resources` | `(ip: str, port: int) → list` | list[str] | Returns ordered VISA candidate strings. |
| `find_usb_resource` | `(rm) → str \| None` | str or None | Searches INSTR/INST/wildcard patterns. |
| `detect_vendor` | `(idn: str) → str` | str | Returns LECROY / TEKTRONIX / KEYSIGHT / RIGOL / SIGLENT / UNKNOWN. |
| `vicp_capture` | `(ip, save_path, timeout_sec) → bool` | bool | Full native VICP capture. LeCroy only. |
| `scpi_capture` | `(resource_str, save_path, timeout_ms) → bool` | bool | VISA-based capture with suffix retry and VICP fallback. |
| `_screen_dump` | `(scope, vendor) → bytes \| None` | bytes | Dispatches to vendor-specific implementation. |
| `_dump_lecroy` | `(scope, color) → bytes` | bytes | HCSU + SCREEN_DUMP via VISA write/read_raw. |
| `_dump_tektronix` | `(scope, color) → bytes` | bytes | HARDcopy START via VISA. |
| `_dump_keysight` | `(scope, color) → bytes` | bytes | `:DISP:DATA? PNG` via query_binary_values. |
| `_dump_rigol` | `(scope, color) → bytes` | bytes | `:DISP:DATA?` with firmware-variant fallback. |
| `_vicp_send` | `(sock, cmd) → None` | — | Wraps ASCII command in VICP 8-byte header. |
| `_vicp_recv` | `(sock) → bytes` | bytes | Accumulates all DATA frames until EOI or socket close. |
| `_dump_lecroy_vicp_raw` | `(ip, color, timeout_sec) → bytes` | bytes | Raw socket HCSU + SCREEN_DUMP without IDN check. |
| `_strip_ieee_block` | `(data: bytes) → bytes` | bytes | Strips `#N<len>` IEEE 488.2 header if present. |
| `_save_image` | `(data, path) → None` | — | Pillow PNG save with raw BMP fallback. |
| `try_http_auth` | `(ip, user, pwd, timeout) → None` | — | Silent HTTP Basic Auth handshake. |
| `main` | `() → None` | — | Entry point. Branches USB / Ethernet. |

---

## scope_scanner.py

`scope_scanner.py` performs a full discovery pass of all instruments reachable from the local machine. Ethernet and USB scans run **in parallel threads**. Results are only reported for hosts that respond with a valid `*IDN?` string — bare TCP port opens are ignored.

### Scanner Configuration

| Variable | Default | Description |
|---|---|---|
| `SCAN_ETHERNET` | `True` | Enable Ethernet subnet scan. |
| `SCAN_USB` | `True` | Enable USB-TMC VISA scan. |
| `SUBNET` | `""` | Override subnet, e.g. `"192.168.1.0/24"`. Empty = auto-detect all active NICs. |
| `SCPI_PORTS` | `[5025, 1861, 80]` | TCP ports probed on each host. Port 1861 = VICP, 5025 = raw SCPI. |
| `MAX_WORKERS` | `64` | Concurrent TCP connection threads per subnet. |
| `TCP_TIMEOUT` | `0.5` | Per-host TCP connect timeout (seconds). Keep low for fast sweeps. |
| `IDN_TIMEOUT` | `3` | Seconds to wait for `*IDN?` response after port is found open. |
| `CSV_OUTPUT` | `""` | File path to write results as CSV. Empty = console only. |

### Ethernet Scan — `get_all_subnets()`

Implements a 3-tier fallback to discover all active IPv4 NICs:

1. **psutil (preferred)** — Iterates `psutil.net_if_addrs()` filtered by active interfaces. Constructs CIDR from each IPv4 address. Skips loopback and APIPA.
2. **`socket.getaddrinfo` hostname trick** — Resolves the machine's hostname. Used when psutil is not installed. Assumes /24 subnet mask.
3. **UDP routing trick** — Creates a UDP socket and calls `connect("8.8.8.8", 80)`. The kernel selects the default-route interface without sending any packets. Last resort — only discovers the single default-route NIC.

### `scan_host()` — Per-Host Probe

Only returns a result if a valid `*IDN?` query elicits a non-empty response — a TCP port open alone is not sufficient.

### `query_idn()` — Raw SCPI over TCP

Sends `*IDN?\n` as raw bytes on a plain TCP socket. Works for both port 5025 (raw SCPI) and port 1861 (VICP) — on VICP port, LeCroy accepts raw text commands without the 8-byte framing header for simple queries.

### API Reference — `scope_scanner.py`

| Function | Signature | Returns | Notes |
|---|---|---|---|
| `get_all_subnets` | `() → list[tuple[str,str]]` | list of (label, cidr) | psutil → getaddrinfo → UDP trick fallback chain. |
| `tcp_probe` | `(ip, port, timeout) → bool` | bool | Single TCP connect attempt. |
| `query_idn` | `(ip, port, timeout) → str` | str | Sends `*IDN?\n`; reads until newline or timeout. |
| `detect_vendor` | `(idn: str) → str` | str | Same logic as lecroy_capture.py. |
| `scan_host` | `(ip: str) → dict \| None` | dict or None | Probes all SCPI_PORTS; returns result only on valid IDN. |
| `scan_ethernet` | `(subnet, label) → list[dict]` | list[dict] | ThreadPoolExecutor sweep with live progress bar. |
| `scan_all_ethernet` | `(subnets) → list[dict]` | list[dict] | Iterates all NICs; deduplicates by IP. |
| `scan_usb` | `() → tuple[list, list]` | (results, log) | Buffered output; prints after ETH bar finishes. |
| `print_results` | `(results: list) → None` | — | Formatted table output with fixed column widths. |
| `save_csv` | `(results, path) → None` | — | Writes CSV with DictWriter. |
| `main` | `() → None` | — | Parallel ETH+USB launch; sequential display. |

---

## Protocol Reference

| Protocol | Port | Transport | Notes |
|---|---|---|---|
| VICP | 1861/TCP | Raw TCP + 8-byte binary header | LeCroy proprietary. Handles both command text and binary image data. Used natively by this toolkit. |
| VXI-11 | 111/TCP (Sun RPC) | ONC RPC / SunRPC | IEEE 488.2 over LAN. VISA resource: `TCPIP::IP::inst0::INSTR`. LeCroy uses this for text SCPI but NOT for image binary transfer. |
| HiSLIP | 4880/TCP | TCP stream | Modern LAN instrument protocol (IVI-6.1). VISA resource: `TCPIP::IP::hislip0::INSTR`. Supported by newer Keysight/Rigol scopes. |
| Raw SCPI | 5025/TCP | Plain TCP | Bare SCPI text over TCP socket. VISA resource: `TCPIP::IP::5025::SOCKET`. Supported by Rigol, some Siglent. |
| USB-TMC | USB | USB class 0xFE sub 0x03 | IEEE 488.2 over USB. Requires NI-VISA or pyvisa-py + libusb. VISA resource: `USB0::VID::PID::serial::INSTR`. |

---

## Vendor SCPI Commands

| Vendor | Config Command | Trigger | Format | Color Control |
|---|---|---|---|---|
| LeCroy | `HCSU DEV,BMP,FORMAT,PORTRAIT,BCKG,{color},DEST,REMOTE,PORT,NET` | `SCREEN_DUMP` | BMP | `BCKG,WHITE` / `BCKG,BLACK` |
| Tektronix | `HARDcopy:PORT GPIB` + `HARDcopy:FORMat BMP` + `HARDcopy:INKSaver ON\|OFF` | `HARDcopy START` | BMP | INKSaver ON=white / OFF=black |
| Keysight | — | `:DISP:DATA? PNG,INKS\|SCR,COL` | PNG (IEEE block) | INKS=white / SCR=black |
| Rigol | `:DISP:DATA? ON,OFF,PNG` | (combined) | PNG (IEEE block) | Second arg: OFF=white / ON=black |
| Siglent | `:DISP:DATA?` | (combined) | PNG (IEEE block) | Limited firmware support |

---

## Dependencies

| Package | Version | Required? | Purpose |
|---|---|---|---|
| `pyvisa` | ≥1.13.0 | **Required** | VISA instrument control abstraction layer. Interfaces with system VISA backend (NI/IVI) or pyvisa-py. |
| `pyvisa-py` | ≥0.7.0 | Fallback | Pure-Python VISA backend when NI-VISA/IVI is not installed. Required for USB-TMC without IVI driver. |
| `pyusb` | ≥1.2.1 | USB only | Low-level USB library used by pyvisa-py for USB-TMC transport. |
| `Pillow` | ≥10.0.0 | Recommended | Image decoding and PNG conversion. Without it, images are saved as raw BMP bytes. |
| `psutil` | ≥5.9.0 | Recommended | Multi-NIC enumeration in scope_scanner.py. Without it, only a single /24 subnet is scanned. |

```
pyvisa>=1.13.0
pyvisa-py>=0.7.0
pyusb>=1.2.1
Pillow>=10.0.0
psutil>=5.9.0
```

---

## Troubleshooting

### Image only 52 bytes via VXI-11

This is expected behaviour for LeCroy scopes in **TCPIP/VICP mode**. VXI-11 returns a short text acknowledgment; the image travels over VICP port 1861. The script handles this automatically — `vicp_capture()` is always tried first.

✅ Verify via: `Utilities → Remote → TCPIP/VICP` on the scope front panel.

---

### `VI_ERROR_RSRC_NFOUND` on USB

LeCroy IVI driver uses `::INST` suffix; standard VISA uses `::INSTR`. The script retries both automatically. If still failing:

- Run `python -m visa info` to list detected resources
- Set `USB_RESOURCE` explicitly to the exact string shown
- Ensure the LeCroy IVI/USB driver is installed (shows in Device Manager)

---

### Scanner only finds one subnet

psutil is not installed or the NIC is down. The script prints which interfaces it detects before scanning. Install psutil (`pip install psutil`) and ensure all relevant NICs have active connections.

---

### Image truncated / Pillow decode error

The VICP transfer completed but not all frames arrived — likely because the `time.sleep(4.0)` post-`SCREEN_DUMP` wait was insufficient for your scope's rendering speed. Increase `TIMEOUT_SEC` in the config or increase the sleep value in `_dump_lecroy_vicp_raw()`.

The frame-by-frame debug output (e.g. `[VICP] frame 1: op=0xC1 len=65,536 total=65,536 eoi=False`) will show exactly how many frames arrived and at what cumulative byte count transfer stopped.

---

### Windows Firewall blocking connections

Add inbound rules for the scope's IP on ports 1861 and 5025, or temporarily disable the firewall profile for private networks. Test connectivity with:

```powershell
Test-NetConnection 1[<This is IP address placeholder>] -Port 1861
Test-NetConnection 1[<This is IP address placeholder>] -Port 5025
```
