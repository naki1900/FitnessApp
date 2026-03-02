import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os

DATA_FILE = "tss_data.csv"

# ===============================
# データ読み込み
# ===============================
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df["Date"] = pd.to_datetime(df["Date"])
    else:
        df = pd.DataFrame(columns=["Date", "TSS"])
    return df


# ===============================
# CTL / ATL / TSB 再計算
# ===============================
def recalc_ctl(df):
    if df.empty:
        return df

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)

    df = df.groupby("Date", as_index=False).sum()

    full_range = pd.date_range(df["Date"].min(), df["Date"].max())
    df = df.set_index("Date").reindex(full_range).fillna(0)
    df.index.name = "Date"
    df = df.reset_index()

    ctl = 0
    atl = 0
    ctl_list = []
    atl_list = []

    for tss in df["TSS"]:
        ctl = ctl + (tss - ctl) / 42
        atl = atl + (tss - atl) / 7
        ctl_list.append(ctl)
        atl_list.append(atl)

    df["CTL"] = ctl_list
    df["ATL"] = atl_list
    df["TSB"] = df["CTL"] - df["ATL"]

    return df


# ===============================
# 初期化
# ===============================
if "data" not in st.session_state:
    st.session_state.data = load_data()

if "ftp" not in st.session_state:
    st.session_state.ftp = 250.0


# ===============================
# レイアウト
# ===============================
left_col, right_col = st.columns([1, 2])

# ======================================================
# 左カラム
# ======================================================
with left_col:

    st.header("パワーからTSS自動計算")

    col1, col2, col3 = st.columns(3)

    with col1:
        ftp_input = st.number_input(
            "FTP",
            min_value=1.0,
            value=st.session_state.ftp,
            step=1.0
        )

    with col2:
        avg_power = st.number_input("平均推定W", min_value=0.0, step=1.0)

    with col3:
        duration_min = st.number_input("時間(分)", min_value=0.0, step=1.0)

    st.session_state.ftp = ftp_input

    if avg_power > 0 and duration_min > 0:
        duration_hour = duration_min / 60
        intensity_factor = avg_power / ftp_input
        calculated_tss = duration_hour * (intensity_factor ** 2) * 100
        st.success(f"計算TSS: {calculated_tss:.2f}")

    st.divider()

    st.header("TSS手動追加")

    input_date = st.date_input("日付", datetime.today())
    input_tss = st.number_input("TSS", min_value=0.0, step=1.0)

    if st.button("追加"):
        new_row = pd.DataFrame({
            "Date": [pd.to_datetime(input_date)],
            "TSS": [input_tss]
        })

        base_df = pd.concat([st.session_state.data, new_row], ignore_index=True)
        base_df.to_csv(DATA_FILE, index=False)
        st.session_state.data = load_data()
        st.success("追加しました")

    st.divider()

    # ===============================
    # 🔥 改善されたデータ一覧
    # ===============================
    st.header("データ一覧（CTL/ATL/TSB含む）")

    calc_df = recalc_ctl(st.session_state.data.copy())

    if not calc_df.empty:

        display_df = calc_df.copy()
        display_df["Date"] = display_df["Date"].dt.date

        st.dataframe(
            display_df,
            use_container_width=True,
            height=500   # ← 高さ拡張
        )

    else:
        st.write("データがありません")


# ======================================================
# 右カラム（グラフ）
# ======================================================
with right_col:
    st.header("パフォーマンス推移")

    calc_df = recalc_ctl(st.session_state.data.copy())

    if not calc_df.empty:

        mode = st.radio("表示期間", ["全期間", "期間指定"])

        if mode == "全期間":
            filtered_df = calc_df
        else:
            start = st.date_input("開始日", calc_df["Date"].min().date())
            end = st.date_input("終了日", calc_df["Date"].max().date())

            filtered_df = calc_df[
                (calc_df["Date"] >= pd.to_datetime(start)) &
                (calc_df["Date"] <= pd.to_datetime(end))
            ]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=filtered_df["Date"], y=filtered_df["CTL"], mode="lines", name="CTL"))
        fig.add_trace(go.Scatter(x=filtered_df["Date"], y=filtered_df["ATL"], mode="lines", name="ATL"))
        fig.add_trace(go.Scatter(x=filtered_df["Date"], y=filtered_df["TSB"], mode="lines", name="TSB"))

        fig.update_layout(hovermode="x unified", yaxis_tickformat=".2f")
        fig.update_traces(hovertemplate="Date: %{x}<br>Value: %{y:.3f}<extra></extra>")

        st.plotly_chart(fig, use_container_width=True)

        tss_fig = go.Figure()
        tss_fig.add_trace(go.Bar(x=filtered_df["Date"], y=filtered_df["TSS"], name="TSS"))
        tss_fig.update_layout(hovermode="x unified")
        tss_fig.update_traces(hovertemplate="Date: %{x}<br>TSS: %{y:.3f}<extra></extra>")

        st.plotly_chart(tss_fig, use_container_width=True)

    else:
        st.write("データがありません")