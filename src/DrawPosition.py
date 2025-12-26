# uwb_realtime_plot.py
import socket
import struct
import threading
import time
from collections import deque

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

import Tr2D

# ==== UWB / UDP 設定 ====
uwb = Tr2D.Tr2D(((450, 0), (0, 0), (0, 450)))  # アンカー座標[cm]
PACK_FMT = "!IfI"  # client_id(uint32), distance(float, cm)
HOST = "0.0.0.0"
PORT = 9999

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))
sock.settimeout(1.0)

# ==== 共有状態 ====
anchor_distance = [0.0, 0.0, 0.0]   # id=1..3 を [0..2] に格納
position_xy = [None, None]          # 最新の (x, y)
trail = deque(maxlen=600)           # 軌跡（約1分ぶん: 0.1s * 600）
lock = threading.Lock()

def udp_receiver():
    """UDP受信スレッド: epochごとに3台そろったときだけ位置を計算する"""
    import time

    # ---- epoch 管理用の状態 ----
    active_epoch = None                # 今処理中の epoch
    active_started_at = 0.0            # この epoch の最初のパケットを受けた時刻
    active_distances = [0.0, 0.0, 0.0] # この epoch の距離
    active_received = set()            # この epoch で届いた client_id の集合

    try:
        while True:
            try:
                data, _addr = sock.recvfrom(1024)
            except socket.timeout:
                # 受信ゼロの時間が続いても特に何もしない
                continue

            # client_id(uint32), epoch(uint32), distance(float) を想定
            if len(data) < struct.calcsize(PACK_FMT):
                continue

            client_id, distance, epoch = struct.unpack(PACK_FMT, data)
            #print(f"Client_ID={client_id}, Distance={int(distance)}, Epoch={epoch}")

            # 無効な ID は無視
            if not (1 <= client_id <= 3):
                continue

            now = time.time()

            # --- 新しい epoch の開始条件 ---
            # 1) まだ何もない
            # 2) 受信した epoch が違う
            # 3) 200ms を超えてしまった（タイムアウト→破棄して新しく始める）
            if (
                active_epoch is None
                or epoch != active_epoch
                or (now - active_started_at) > 0.2
            ):
                active_epoch = epoch
                active_started_at = now
                active_distances = [0.0, 0.0, 0.0]
                active_received = set()

            # この epoch の距離を更新
            active_distances[client_id - 1] = distance
            active_received.add(client_id)

            # 3台ぶんそろったときだけ solve を実行
            if len(active_received) == 3:
                with lock:
                    # 描画側に渡す距離も更新
                    for i in range(3):
                        anchor_distance[i] = active_distances[i]

                    try:
                        x, y = uwb.solve_once(anchor_distance)
                        print(f"x:{x}, y:{y}")
                        position_xy[0], position_xy[1] = float(x), float(y)
                        trail.append((position_xy[0], position_xy[1]))
                    except Exception:
                        # 解が出ないときは無視して次へ
                        pass

                # この epoch は完了扱い → 次の epoch を待つ
                active_epoch = None
                active_received = set()

    finally:
        sock.close()

# ==== 描画セットアップ ====
fig, ax = plt.subplots(figsize=(6, 6))
ax.set_title("UWB Tag Position (cm)")
ax.set_xlabel("X [cm]")
ax.set_ylabel("Y [cm]")

# 表示範囲（アンカー三角を少し余裕を持って囲む）
ax.set_xlim(-50, 500)
ax.set_ylim(-50, 500)
ax.set_aspect("equal", adjustable="box")
ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.5)

# アンカー表示
anchors = [(450, 0), (0, 0), (0, 450)]
ax.scatter([a[0] for a in anchors], [a[1] for a in anchors], s=80, marker="^", label="Anchors")
for i, (ax_x, ax_y) in enumerate(anchors, start=1):
    ax.text(ax_x + 4, ax_y + 4, f"A{i}({ax_x},{ax_y})", fontsize=9)

# 現在位置と軌跡のアーティスト
(point_line,) = ax.plot([], [], "o", markersize=8, label="Tag")
(trail_line,) = ax.plot([], [], "-", linewidth=1.5, alpha=0.8, label="Trail")

# 距離のテキスト表示
text_anchor = ax.text(0.02, 0.98, "", transform=ax.transAxes, va="top", fontsize=9,
                      family="monospace")

ax.legend(loc="lower right")

def fmt_distances(d):
    return f"a1:{int(d[0])}cm  a2:{int(d[1])}cm  a3:{int(d[2])}cm"

def update(_frame):
    # 共有状態を読み取り
    with lock:
        x, y = position_xy[0], position_xy[1]
        d = anchor_distance[:]
        tr = list(trail)

    # テキスト（距離）
    text_anchor.set_text(fmt_distances(d))

    # 軌跡
    if tr:
        xs, ys = zip(*tr)
        trail_line.set_data(xs, ys)
    else:
        trail_line.set_data([], [])

    # 現在位置
    if x is not None and y is not None:
        point_line.set_data([x], [y])
    else:
        point_line.set_data([], [])

    return point_line, trail_line, text_anchor

def main():
    # UDP受信スレッド起動
    th = threading.Thread(target=udp_receiver, daemon=True)
    th.start()

    # 100ms周期で画面更新（あなたの送信周期に合わせて調整OK）
    ani = FuncAnimation(fig, update, interval=100, blit=True)
    try:
        plt.show()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
