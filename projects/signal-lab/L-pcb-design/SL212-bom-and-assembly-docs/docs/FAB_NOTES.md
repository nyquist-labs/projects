# Fabrication and assembly notes — preamp

| Item | Specification |
|---|---|
| Layers | 2 (F.Cu, B.Cu) |
| Board size | 50 × 36 mm, 1 mm corner radius |
| Material / thickness | FR-4, 1.6 mm, 1 oz copper both sides |
| Min track / space | 0.15 mm / 0.2 mm (design uses ≥ 0.25 mm tracks) |
| Min drill / via | 0.3 mm drill, 0.6 mm pad (vias tented) |
| Finish / mask / legend | HASL lead-free or ENIG; green mask; white legend |
| Impedance control | not required |

**Files:** `fab/*.gbr` (RS-274X copper, mask, paste, legend, outline), `fab/*.drl` (Excellon, plated), `data/bom.csv`, `data/pick_and_place.csv`
(top side, mm, rotation counter-clockwise, origin at the lower-left board corner).

**Assembly:** SMD parts on top only; THT parts (J1, J2, J3) hand-soldered after reflow. U1 pin 1 is marked on the assembly drawing.
Polarised parts: none among the SMD parts (ceramic capacitors).
