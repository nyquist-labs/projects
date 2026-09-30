from eelab import *
from eelab import firmware as fwk
import socket, threading, struct, time

META = dict(
    id="SL-150", title="MQTT publisher: packet encoding and a round-trip test", level="M",
    tools="C firmware (MQTT 3.1.1 CONNECT/PUBLISH/PINGREQ encoder over TCP sockets) + a minimal local broker in Python",
    summary="Implement the MQTT 3.1.1 packets an IoT sensor needs in C, publish 100 sensor readings over TCP to a tiny local "
            "broker, and verify packet layout (remaining-length varint, topic, QoS 0/1 PUBACK) and end-to-end delivery.",
    problem="IoT devices speak MQTT. What exactly is inside those packets, and can a hand-written client interoperate with a "
            "broker?",
    theory=r"""Fixed header: type/flags byte + 'remaining length' as a base-128 varint (1 byte up to 127, 2 bytes up to 16,383). PUBLISH (QoS 0) = 2 + topic
length + payload; QoS 1 adds a 2-byte packet id and the broker answers PUBACK. For topic 'lab/temp' (8 B) and a 5-B payload, a QoS-0
PUBLISH is 2 + 2 + 8 + 5 = 17 bytes.""",
    method="""The C client connects to 127.0.0.1 (no external network), sends CONNECT (keep-alive 60 s), 50 QoS-0 and 50 QoS-1 PUBLISH messages and a
PINGREQ, then DISCONNECT. The Python broker parses every packet, records sizes, acknowledges QoS-1 publishes and the ping. A Wokwi ESP32
sketch using PubSubClient is included for running against a public broker in the browser.""",
)

C = r"""
#include "hal_sim.h"
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>
static int enc_len(uint8_t *b, int len) { int n = 0; do { uint8_t d = len % 128; len /= 128; if (len) d |= 0x80; b[n++] = d; } while (len); return n; }
static int put_str(uint8_t *b, const char *s) { int l = (int)strlen(s); b[0] = l >> 8; b[1] = l & 0xFF; memcpy(b + 2, s, l); return l + 2; }
static void sendall(int fd, uint8_t *b, int n) { int s = 0; while (s < n) { int k = (int)send(fd, b + s, n - s, 0); if (k <= 0) exit(3); s += k; } }
static int recvn(int fd, uint8_t *b, int n) { int s = 0; while (s < n) { int k = (int)recv(fd, b + s, n - s, 0); if (k <= 0) return -1; s += k; } return s; }
int main(int argc, char **argv) {
    int port = atoi(argv[1]); log_pins = 0;
    int fd = socket(AF_INET, SOCK_STREAM, 0); struct sockaddr_in a = {0}; a.sin_family = AF_INET; a.sin_port = htons(port); a.sin_addr.s_addr = htonl(0x7F000001);
    if (connect(fd, (struct sockaddr *)&a, sizeof a)) return 2;
    uint8_t body[256], pkt[300]; int n = 0;
    n += put_str(body + n, "MQTT"); body[n++] = 4; body[n++] = 0x02; body[n++] = 0; body[n++] = 60; n += put_str(body + n, "eelab-sensor-01");
    int h = 0; pkt[h++] = 0x10; h += enc_len(pkt + h, n); memcpy(pkt + h, body, n); sendall(fd, pkt, h + n);
    uint8_t ack[4]; recvn(fd, ack, 4); printf("RES connack_rc %d\n", ack[3]);
    int pubacks = 0;
    for (int i = 0; i < 100; i++) {
        int qos = i < 50 ? 0 : 1; char payload[16]; snprintf(payload, sizeof payload, "%.2f", 20.0 + 0.05 * i);
        n = 0; n += put_str(body + n, "lab/temp"); if (qos) { body[n++] = (i >> 8) & 0xFF; body[n++] = i & 0xFF; }
        int pl = (int)strlen(payload); memcpy(body + n, payload, pl); n += pl;
        h = 0; pkt[h++] = 0x30 | (qos << 1); h += enc_len(pkt + h, n); memcpy(pkt + h, body, n); sendall(fd, pkt, h + n);
        printf("S %d %d\n", qos, h + n);
        if (qos) { uint8_t pa[4]; if (recvn(fd, pa, 4) == 4 && pa[0] == 0x40 && ((pa[2] << 8) | pa[3]) == i) pubacks++; }
    }
    printf("RES pubacks %d\n", pubacks);
    uint8_t ping[2] = {0xC0, 0}; sendall(fd, ping, 2); uint8_t pr[2]; recvn(fd, pr, 2); printf("RES pingresp %d\n", pr[0] == 0xD0);
    uint8_t disc[2] = {0xE0, 0}; sendall(fd, disc, 2); close(fd);
    return 0;
}
"""
INO = r"""
// Wokwi ESP32 + PubSubClient: publishes a reading every 2 s to a public test broker (runs in the browser simulator)
#include <WiFi.h>
#include <PubSubClient.h>
WiFiClient net; PubSubClient mqtt(net);
void setup() { Serial.begin(115200); WiFi.begin("Wokwi-GUEST", "", 6); while (WiFi.status() != WL_CONNECTED) delay(100);
  mqtt.setServer("test.mosquitto.org", 1883); }
void loop() { if (!mqtt.connected()) mqtt.connect("eelab-wokwi-demo"); mqtt.loop();
  static uint32_t t = 0; if (millis() - t > 2000) { t = millis(); char b[16]; dtostrf(20 + random(100) / 100.0, 0, 2, b); mqtt.publish("eelab/demo/temp", b); } }
"""


class Broker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.s = socket.socket(); self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind(("127.0.0.1", 0)); self.s.listen(1); self.port = self.s.getsockname()[1]
        self.packets, self.msgs = [], []

    def run(self):
        c, _ = self.s.accept()
        def rd(n):
            b = b""
            while len(b) < n:
                k = c.recv(n - len(b))
                if not k: raise EOFError
                b += k
            return b
        try:
            while True:
                h = rd(1)[0]; mult, L = 1, 0; nb = 0
                while True:
                    d = rd(1)[0]; nb += 1; L += (d & 127) * mult; mult *= 128
                    if not d & 128: break
                body = rd(L); typ = h >> 4
                self.packets.append((typ, 1 + nb + L))
                if typ == 1: c.sendall(bytes([0x20, 2, 0, 0]))
                elif typ == 3:
                    qos = (h >> 1) & 3; tl = struct.unpack(">H", body[:2])[0]; topic = body[2:2 + tl].decode(); o = 2 + tl
                    pid = None
                    if qos: pid = body[o:o + 2]; o += 2
                    self.msgs.append((topic, body[o:].decode(), qos))
                    if qos == 1: c.sendall(bytes([0x40, 2]) + pid)
                elif typ == 12: c.sendall(bytes([0xD0, 0]))
                elif typ == 14: break
        except EOFError:
            pass


def run(p):
    b = Broker(); b.start()
    log = fwk.run(p, {"mqtt_pub.c": C, "esp32_mqtt.ino": INO}, args=(b.port,))
    b.join(timeout=10)
    r = fwk.results(log)
    p.compare("CONNACK return code (0 = accepted)", 0, r["connack_rc"], "", kind="abs")
    p.compare("Messages received by the broker", 100, len(b.msgs), "", kind="abs")
    p.compare("QoS-1 PUBACKs matched to packet IDs", 50, r["pubacks"], "", kind="abs")
    p.compare("PINGRESP received", 1, r["pingresp"], "", kind="abs")
    S = fwk.rows(log, "S")
    q0 = S[S[:, 0] == 0][:, 1]
    p.compare("QoS-0 PUBLISH size for 'lab/temp' + 5-byte payload", 17, float(np.median(q0)), "bytes", kind="abs")
    ok_payload = all(abs(float(m[1]) - (20 + 0.05 * i)) < 1e-9 for i, m in enumerate(b.msgs))
    p.compare("Payloads delivered intact and in order", 1, int(ok_payload), "", kind="abs")
    types = {1: "CONNECT", 3: "PUBLISH", 12: "PINGREQ", 14: "DISCONNECT"}
    counts = {}
    for t, n in b.packets:
        counts[types.get(t, t)] = counts.get(types.get(t, t), 0) + n
    fig, ax = p.fig()
    ax.bar(list(counts), list(counts.values()), color=C_MEAS)
    style_axes(ax, "packet type", "total bytes sent", "Bytes on the wire per packet type (100 publishes)", legend=False)
    p.save(fig, "mqtt", "PUBLISH dominates; QoS-1 messages cost 2 extra bytes each plus a 4-byte PUBACK back.")
    p.section("Browser version", "`firmware/esp32_mqtt.ino` runs in Wokwi's ESP32 simulator (Wokwi-GUEST Wi-Fi) against the public test broker test.mosquitto.org — not executed here, to keep this repository's tests offline.")
    p.discuss("""A hand-written client interoperates with an independent broker implementation: CONNECT is accepted, all 100 readings arrive in
order, every QoS-1 message is acknowledged with the matching packet ID, and a QoS-0 publish is exactly the 17 bytes computed from
the spec. MQTT's small fixed header is why it suits constrained devices; QoS 1 costs a round trip per message, which matters on
high-latency cellular links.""")
