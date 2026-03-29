# Factory Domain Knowledge

## Factory Overview
| Factory | Produces | Role |
|---------|----------|------|
| FA      | P1       | Independent raw material producer |
| FB      | P2, P12  | Raw material + assembles P12 using P1(from FA) + P2 |
| FC      | P3, P13, P23 | Raw material + assembles P13 (P1+P3) and P23 (P2+P3) |
| FD      | P4, P234 | Raw material + assembles P234 using P23(from FC) + P4 |

## Supply Chain (Logistics Flow)
- **FA → FB**: P1 shipped to FB for P12 assembly
- **FA → FC**: P1 shipped to FC for P13 assembly
- **FB → FC**: P2 shipped to FC for P23 assembly
- **FC → FD**: P23 shipped to FD for P234 assembly

## Assembly Relationships
- **P12** = P1 (FA) + P2 (FB), assembled at FB
- **P13** = P1 (FA) + P3 (FC), assembled at FC
- **P23** = P2 (FB) + P3 (FC), assembled at FC
- **P234** = P23 (FC) + P4 (FD), assembled at FD

## Factory Dependencies
- **FA**: Independent
- **FB**: Depends on FA for P1
- **FC**: Depends on FA for P1, FB for P2
- **FD**: Depends on FC for P23

## InfluxDB Metric Mapping (internal — never show to user)
| Product | factory_id | metric field      |
|---------|-----------|-------------------|
| P1      | fa        | p1                |
| P2      | fb        | p2                |
| P3      | fc        | p3                |
| P4      | fd        | p4                |
| P12     | fb        | p12               |
| P13     | fc        | p13               |
| P23     | fc        | p23               |
| P234    | fd        | p234              |
| P1 queue| fa        | p1_wait_queue     |
| P2 queue| fb        | p2_wait_queue     |
| P23 queue| fc       | p23_wait_queue    |

## Tool Selection Rules
- **"过去N分钟/最近N分钟/past N minutes"** → call `get_production_delta(minutes=N)` → show **Table 1 + Table 2** with "Produced (N min)" column
- **"物流/上下游/待运输/等待队列/wait queue"** → call `get_current_status()` → show **Table 3 only**
- **"总体情况/生产总览/overview/overall"** → call `get_current_status()` → show **Table 1 + Table 2 + Table 3**
- **"趋势/变化/上升/下降/trend/rising/falling"** → call `get_trend_data(minutes=N)` → describe per-minute production changes in plain text

## Fixed Output Table Formats

**Table 1 — Raw Material Output**
| Factory | Product | Produced (N min) / Total |
|---------|---------|--------------------------|
| FA | P1 | value |
| FB | P2 | value |
| FC | P3 | value |
| FD | P4 | value |

**Table 2 — Assembly Output**
| Factory | Product | Produced (N min) / Total |
|---------|---------|--------------------------|
| FB | P12  | value |
| FC | P13  | value |
| FC | P23  | value |
| FD | P234 | value |

**Table 3 — Logistics Waiting Queue**
| Factory | Product | Queue |
|---------|---------|-------|
| FA | P1  | value |
| FB | P2  | value |
| FC | P23 | value |

Add a one-line bottleneck note after Table 3 only if any queue value > 10.

## Machine Control Parameters
- **Production Speed** (`set_production_speed`): InterArrival time in seconds, numeric only, e.g. `4`. No unit suffix.
- **Planned Quantity** (`set_plan_quantity`): Integer, total targeted production count.
- **Factory IDs**: `fa_p1`, `fb_p2`, `fc_p3`, `fd_p4`, or `all`.

## Emergency Shutdown & Restore
- `emergency_shutdown` sets factory maxnum to 0 **and saves the previous quantity as a backup**.
- To resume after shutdown, always use `restart_production` — it reads the backup and restores the original plan quantity automatically.
- **Never use `set_production_speed` to restore from a shutdown.** Speed and quantity are independent parameters.
- If the user says "restart", "resume", "end maintenance", "bring back online", "restore production", or similar → call `restart_production`, not `set_plan_quantity` or `set_production_speed`.
