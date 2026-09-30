#include "hal_sim.h"
int main(int argc, char **argv) {
    double tau = atof(argv[1]); log_pins = 0;
    const double dt = 0.01; double est = 0, gyro_only = 0; double se = 0, sg = 0, sa = 0; int n = 0;
    rng_state = 12345;
    for (int k = 0; k < 12000; k++) {
        double t = k * dt;
        double th = 30 * sin(0.2 * t) + 10 * sin(0.9 * t + 1);
        double w = 30 * 0.2 * cos(0.2 * t) + 10 * 0.9 * cos(0.9 * t + 1);
        double acc = th + 3.0 * rndn() + 4.0 * sin(2 * 3.14159 * 20 * t);
        double gyr = w + 0.5 + 0.05 * rndn() / sqrt(dt) * 0.1;
        double a = tau / (tau + dt);
        est = a * (est + gyr * dt) + (1 - a) * acc;
        gyro_only += gyr * dt;
        if (t > 10) { se += (est - th) * (est - th); sg += (gyro_only - th) * (gyro_only - th); sa += (acc - th) * (acc - th); n++; }
        if (k % 10 == 0) printf("X %f %f %f %f %f\n", t, th, est, gyro_only, acc);
    }
    printf("RES rms %f\nRES rms_gyro %f\nRES rms_acc %f\n", sqrt(se / n), sqrt(sg / n), sqrt(sa / n));
    return 0;
}
