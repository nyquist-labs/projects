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
