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
