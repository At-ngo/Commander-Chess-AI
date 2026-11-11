# Thư viện & Cấu hình Dùng chung (`experiments/common`)

## Mục tiêu

Cung cấp bộ cấu hình và các module Python dùng chung để mọi notebook thực nghiệm (`07`–`13`) tái sử dụng thống nhất, dễ bảo trì và tái lập được kết quả.

## Cấu trúc module

| File | Chức năng |
| --- | --- |
| `__init__.py` | Đánh dấu package Python và export các API chính |
| `config.py` | Cấu hình số ván (`200`), danh sách seed (`2026`, `42`, ...), `draw_on_max_turns: false`, `budget_modes` (`1000 ms`), đường dẫn & nạp YAML |
| `experiment_config.yaml` | File dữ liệu cấu hình dùng chung (`defaults`, `agent_configs`, `experiments`) |
| `imports.py` | Tập hợp các import thường dùng (stdlib, `numpy`, `pandas`, `matplotlib`, `seaborn`, `scipy`, `statsmodels`, `psutil`, `tqdm`, `pytest`, `wandb`, Engine, Agents) |
| `agent_factory.py` | Khởi tạo Agent theo tên và cấu hình (`create_agent`, `register_agent`, `resolve_agent_config_id`) |
| `match_runner.py` | Chạy một ván đấu giữa hai Agent qua Game Engine chính thức, phân biệt `completed`/`truncated`/`timeout`/`error`, tính `state_hash` |
| `tournament.py` | Tổ chức đối đầu / Round-robin, đảo màu Đỏ/Xanh (`side_balance`), quay vòng `seeds`, `tqdm` và tùy chọn đa tiến trình (`max_workers`) |
| `metrics.py` | Win Rate, Score (`(wins + 0.5 * draws) / completed_games`), `pair_results.csv`, Wilson/Bootstrap CI, trung bình, p95, tách phe Đỏ/Xanh |
| `statistics.py` | Wilson CI, Bootstrap CI, phân tích độ nhạy (`sensitivity_analysis`) |
| `visualization.py` | Vẽ biểu đồ cột, W/D/L, phân phối lượt đi, đường độ nhạy, heatmap, ma trận đối đầu |
| `data_logger.py` | Lưu `config.json`, `environment.json`, `moves.csv`, `games.csv`, `pair_results.csv`, `game_records/*.json` tại `research/results/` và tích hợp `wandb` (`research/runs/`) |
| `profiling.py` | Đo RAM, VRAM (nếu có CUDA), CPU và thời gian xử lý |
| `reproducibility.py` | Thiết lập seed, ghi phiên bản Git/môi trường và cấu hình thực tế |

## Cách gọi nhanh trong notebook (`research/experiments/`)

```python
from common.imports import *
from common import (
    load_experiment_config,
    set_global_seed,
    create_agent,
    run_head_to_head,
    summarize_agent_matches,
    summarize_pair_results,
)

cfg = load_experiment_config("07_test_random_agent")
set_global_seed(cfg["seed"])
```

## Quy tắc

- Dùng YAML hoặc JSON cho file cấu hình dữ liệu.
- Kiểm tra cấu hình trước khi chạy (`validate_experiment_config`).
- Không để bí mật (`WANDB_API_KEY`, ...) trong cấu hình; nạp qua `.env`.
- Mặc định xuất artifact kết quả vào `research/results/` (`RESULTS_DIR`) và log chạy W&B vào `research/runs/` (`RUNS_DIR`), tránh ghi đè kết quả cũ (`allow_overwrite: false`).
