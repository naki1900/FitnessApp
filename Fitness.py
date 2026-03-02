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

    # 同日複数行対応（合計）
    df = df.groupby("Date", as_index=False).sum()

    # 日付を連続化（未入力日はTSS=0）
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


# ===============================
# レイアウト
# ===============================
left_col, right_col = st.columns([1, 2])

# ======================================================
# 左カラム（入力＋一覧）
# ======================================================
with left_col:
    st.header("TSS追加")

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
    st.header("データ一覧（TSS>0のみ表示）")

    raw_df = st.session_state.data.copy()
    raw_df = raw_df[raw_df["TSS"] > 0]

    if not raw_df.empty:

        raw_df_display = raw_df.copy()
        raw_df_display["Date"] = raw_df_display["Date"].dt.date

        # 一覧表示
        st.dataframe(raw_df_display, use_container_width=True)

        st.divider()

        selected_index = st.selectbox(
            "削除する行を選択",
            raw_df_display.index,
            format_func=lambda x: f"{raw_df_display.loc[x, 'Date']} - TSS {raw_df_display.loc[x, 'TSS']}"
        )

        if st.button("選択行を削除"):
            st.session_state.data = st.session_state.data.drop(selected_index)
            st.session_state.data.to_csv(DATA_FILE, index=False)
            st.session_state.data = load_data()
            st.success("削除しました")

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

        # ===============================
        # CTL / ATL / TSB 折れ線
        # ===============================
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=filtered_df["Date"],
            y=filtered_df["CTL"],
            mode="lines",
            name="CTL"
        ))

        fig.add_trace(go.Scatter(
            x=filtered_df["Date"],
            y=filtered_df["ATL"],
            mode="lines",
            name="ATL"
        ))

        fig.add_trace(go.Scatter(
            x=filtered_df["Date"],
            y=filtered_df["TSB"],
            mode="lines",
            name="TSB"
        ))

        fig.update_layout(
            hovermode="x unified",
            yaxis_tickformat=".2f"
        )

        fig.update_traces(
            hovertemplate="Date: %{x}<br>Value: %{y:.3f}<extra></extra>"
        )

        st.plotly_chart(fig, use_container_width=True)

        # ===============================
        # TSS 棒グラフ
        # ===============================
        tss_fig = go.Figure()

        tss_fig.add_trace(go.Bar(
            x=filtered_df["Date"],
            y=filtered_df["TSS"],
            name="TSS"
        ))

        tss_fig.update_layout(
            hovermode="x unified"
        )

        tss_fig.update_traces(
            hovertemplate="Date: %{x}<br>TSS: %{y:.3f}<extra></extra>"
        )

        st.plotly_chart(tss_fig, use_container_width=True)

    else:
        st.write("データがありません")