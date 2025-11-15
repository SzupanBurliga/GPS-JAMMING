#!/usr/bin/env python3

import argparse
import csv
import json
import signal
import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional


class CSVRequestHandler(BaseHTTPRequestHandler):
    writer: Optional[csv.writer] = None
    csv_file = None
    lock = threading.Lock()
    header_written = False

    def do_POST(self):
        if self.path != "/data":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400)
            return

        payload = self.rfile.read(length)
        try:
            data = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400)
            return

        elapsed = data.get("elapsed_time")
        position = data.get("position") or {}
        lat = position.get("lat")
        lon = position.get("lon")

        with self.lock:
            if self.writer:
                self.writer.writerow([elapsed, lat, lon])
                if self.csv_file:
                    self.csv_file.flush()

        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format, *args):
        # wyciszamy standardowe logi HTTP
        pass


def parse_args():
    parser = argparse.ArgumentParser(
        description="Uruchom gnssdec i zbierz CSV (elapsed_time, lat, lon)",
        add_help=False,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-g", action="store_true", help="tryb GPS")
    group.add_argument("-a", action="store_true", help="tryb Galileo")
    group.add_argument("-l", action="store_true", help="tryb GLONASS")
    parser.add_argument(
        "-h",
        "--hold",
        action="store_true",
        help="włącza tryb hold pozycji w gnssdec",
    )
    parser.add_argument(
        "--help",
        action="help",
        help="pokaż ten komunikat i zakończ",
    )
    parser.add_argument(
        "input_file", type=Path, help="ścieżka do nagrania (np. *.bin)"
    )
    return parser.parse_args()


def resolve_flag(args) -> str:
    if args.a:
        return "-a"
    if args.l:
        return "-l"
    return "-g"


def main():
    args = parse_args()
    input_path = args.input_file.resolve()
    if not input_path.exists():
        raise SystemExit(f"Plik {input_path} nie istnieje")

    flag = resolve_flag(args)
    gnssdec_path = Path(__file__).resolve().parents[1] / "bin" / "gnssdec"
    if not gnssdec_path.exists():
        raise SystemExit(f"Nie znaleziono gnssdec pod {gnssdec_path}")

    stem = input_path.name
    if stem.endswith(".bin"):
        stem = stem[:-4]
    csv_path = input_path.with_name(f"{stem}.csv")

    server = HTTPServer(("127.0.0.1", 1234), CSVRequestHandler)
    retcode = 0

    with csv_path.open("w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        CSVRequestHandler.writer = writer
        CSVRequestHandler.header_written = False
        CSVRequestHandler.csv_file = csv_file
        writer.writerow(["elapsed_time", "lat", "lon"])

        server_thread = threading.Thread(
            target=server.serve_forever, name="HTTPServer", daemon=True
        )
        server_thread.start()

        cmd = [str(gnssdec_path), flag]
        if args.hold:
            cmd.append("-h")
        cmd.append(str(input_path))
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        try:
            retcode = proc.wait()
        except KeyboardInterrupt:
            proc.send_signal(signal.SIGINT)
            retcode = proc.wait()
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join()

    if retcode != 0:
        raise SystemExit(retcode)


if __name__ == "__main__":
    main()

