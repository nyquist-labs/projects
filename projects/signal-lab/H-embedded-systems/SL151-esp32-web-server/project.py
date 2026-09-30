from eelab import *
from eelab import firmware as fwk
import urllib.request, threading, time, subprocess, shutil, socket

META = dict(
    id="SL-151", title="Embedded web server: control page and REST endpoint", level="M",
    tools="C firmware (single-threaded HTTP/1.0 server on sockets, like an ESP32 WebServer loop) + Python HTTP client test",
    summary="Serve a control page and a tiny JSON API from 'device' firmware, toggle a simulated LED over HTTP and read a "
            "simulated sensor; measure request latency and verify HTTP framing (status line, headers, Content-Length).",
    problem="Many IoT gadgets are configured through a web page served by the device itself. What is the minimum HTTP a "
            "microcontroller must implement, and how responsive is it?",
    theory=r"""HTTP/1.0 over TCP: parse the request line (`GET /path HTTP/1.0`), answer with a status line, headers (Content-Type, Content-Length) and the
body, then close. A single-threaded server handles one request at a time, so latency ≈ processing time + loopback RTT (≪ 1 ms on localhost), and
throughput ≈ 1/latency.""",
    method="""Server bound to 127.0.0.1 (random free port) with routes `/` (HTML page), `/api/led?on=1|0`, `/api/sensor` (JSON), 404 otherwise. Python client
issues 200 mixed requests, checks status codes, Content-Length = body length, LED state round-trip and JSON validity; latencies recorded.""",
)

C = r"""
#include "hal_sim.h"
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>
static int led = 0; static double temp = 21.5;
static const char *PAGE = "<!doctype html><html><head><meta name=viewport content='width=device-width'><title>eelab device</title></head>"
  "<body><h1>eelab device</h1><p>LED: <a href='/api/led?on=1'>on</a> | <a href='/api/led?on=0'>off</a></p>"
  "<p>Sensor: <span id=t>?</span> &deg;C</p><script>fetch('/api/sensor').then(r=>r.json()).then(j=>t.textContent=j.temp_c)</script></body></html>";
static void reply(int c, int code, const char *type, const char *body) {
    char hdr[256]; int bl = (int)strlen(body);
    int hl = snprintf(hdr, sizeof hdr, "HTTP/1.0 %d %s\r\nContent-Type: %s\r\nContent-Length: %d\r\nConnection: close\r\n\r\n", code, code == 200 ? "OK" : "Not Found", type, bl);
    send(c, hdr, hl, 0); send(c, body, bl, 0);
}
int main(int argc, char **argv) {
    int port = atoi(argv[1]), nreq = atoi(argv[2]);
    int s = socket(AF_INET, SOCK_STREAM, 0); int one = 1; setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
    struct sockaddr_in a = {0}; a.sin_family = AF_INET; a.sin_port = htons(port); a.sin_addr.s_addr = htonl(0x7F000001);
    if (bind(s, (struct sockaddr *)&a, sizeof a) || listen(s, 8)) return 2;
    printf("READY\n"); fflush(stdout);
    for (int k = 0; k < nreq; k++) {
        int c = accept(s, 0, 0); char req[1024] = {0}; int n = (int)recv(c, req, sizeof req - 1, 0); (void)n;
        char path[256] = {0}; sscanf(req, "GET %255s", path);
        char body[256];
        if (!strcmp(path, "/")) reply(c, 200, "text/html", PAGE);
        else if (!strncmp(path, "/api/led", 8)) { char *q = strstr(path, "on="); if (q) led = q[3] == '1'; digitalWrite(2, led);
            snprintf(body, sizeof body, "{\"led\": %d}", led); reply(c, 200, "application/json", body); }
        else if (!strcmp(path, "/api/sensor")) { temp += 0.01; snprintf(body, sizeof body, "{\"temp_c\": %.2f, \"led\": %d}", temp, led); reply(c, 200, "application/json", body); }
        else reply(c, 404, "text/plain", "not found");
        close(c);
    }
    close(s); return 0;
}
"""


def run(p):
    import json
    so = socket.socket(); so.bind(("127.0.0.1", 0)); port = so.getsockname()[1]; so.close()
    fw = p.dir / "firmware"; fw.mkdir(exist_ok=True)
    fwk.shutil.copy(fwk.HAL, fw / "hal_sim.h")
    p.write("firmware/webserver.c", C.strip() + "\n", "firmware source")
    (fw / "build").mkdir(exist_ok=True)
    subprocess.run([shutil.which("cc"), "-O2", "-o", "build/web", "webserver.c", "-lm"], cwd=fw, check=True)
    N = 200
    proc = subprocess.Popen([str(fw / "build" / "web"), str(port), str(N)], stdout=subprocess.PIPE, text=True)
    proc.stdout.readline()
    lat, codes, len_ok, led_ok, json_ok = [], [], 0, 0, 0
    for i in range(N):
        path = ["/", "/api/sensor", f"/api/led?on={i % 2}", "/nope"][i % 4]
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
                body = r.read(); code = r.status; cl = int(r.headers["Content-Length"])
        except urllib.error.HTTPError as e:
            body = e.read(); code = e.code; cl = int(e.headers["Content-Length"])
        lat.append((time.perf_counter() - t0) * 1e3); codes.append(code)
        len_ok += cl == len(body)
        if path.startswith("/api/led"):
            led_ok += json.loads(body)["led"] == i % 2
        if path == "/api/sensor":
            json_ok += isinstance(json.loads(body)["temp_c"], float)
    proc.wait(timeout=10)
    codes = np.array(codes); lat = np.array(lat)
    p.compare("Correct status codes (150 × 200, 50 × 404)", 200, int(np.sum(codes == 200) == 150) * 100 + int(np.sum(codes == 404) == 50) * 100, "", kind="abs")
    p.compare("Content-Length equals body length (all 200 responses)", N, len_ok, "", kind="abs")
    p.compare("LED state round-trips", 50, led_ok, "", kind="abs")
    p.compare("Sensor endpoint returns valid JSON", 50, json_ok, "", kind="abs")
    p.metric("Median request latency (loopback)", float(np.median(lat)), "ms", f"p95 {np.percentile(lat, 95):.2f} ms")
    fig, ax = p.fig()
    ax.hist(lat, 40, color=C_MEAS)
    style_axes(ax, "request latency (ms)", "requests", "200 HTTP requests to the device server", legend=False)
    p.save(fig, "latency", "Loopback latency of the single-threaded server.")
    p.discuss("""The minimal server answers every request with correct HTTP framing (status line, Content-Type, exact Content-Length) and the
LED/sensor API round-trips correctly — enough for any browser to render the control page. On localhost latency is dominated by the
client library; on a real ESP32 it would be set by Wi-Fi (a few ms) and by the single-threaded design, which serialises clients —
the reason ESP-IDF's async server exists.""")
