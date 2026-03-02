import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("CTL / ATL / TSB 管理ツール")

FILE_NAME = "tss_data.csv"

# ==========================
# CTL再計算
# ==========================
def recalc_ctl(df):

    if df.empty:
        return pd.DataFrame(columns=["Date", "TSS", "CTL", "ATL", "TSB"])

    df["Date"] = pd.to_datetime(df["Date"])

    # 同日TSS合算
    df = (
        df.groupby("Date", as_index=False)["TSS"]
        .sum()
        .sort_values("Date")
        .reset_index(drop=True)
    )

    # 日付連続化（0補完）
    full_range = pd.date_range(
        start=df["Date"].min(),
        end=df["Date"].max(),
        freq="D"
    )

    df = df.set_index("Date").reindex(full_range)
    df.index.name = "Date"
    df["TSS"] = df["TSS"].fillna(0)
    df = df.reset_index()

    ctl_list = []
    atl_list = []
    tsb_list = []

    ctl_prev = 0
    atl_prev = 0

    for _, row in df.iterrows():
        tss = row["TSS"]

        ctl = ctl_prev + (tss - ctl_prev) / 42
        atl = atl_prev + (tss - atl_prev) / 7
        tsb = ctl - atl

        ctl_list.append(ctl)
        atl_list.append(atl)
        tsb_list.append(tsb)

        ctl_prev = ctl
        atl_prev = atl

    df["CTL"] = ctl_list
    df["ATL"] = atl_list
    df["TSB"] = tsb_list

    return df


# ==========================
# 初期読み込み
# ==========================
if "data" not in st.session_state:

    if os.path.exists(FILE_NAME):
        df_loaded = pd.read_csv(FILE_NAME)
        st.session_state.data = recalc_ctl(df_loaded)
    else:
        st.session_state.data = pd.DataFrame(
            columns=["Date", "TSS", "CTL", "ATL", "TSB"]
        )

# ==========================
# 2列レイアウト
# ==========================
left_col, right_col = st.columns([1, 2])

# ==========================
# 左列：入力 + 一覧
# ==========================
with left_col:

    st.subheader("TSS追加")

    date = st.date_input("日付")
    tss = st.number_input("TSS", min_value=0.0)

    if st.button("追加"):

        new_row = pd.DataFrame(
            [[pd.to_datetime(date), tss]],
            columns=["Date", "TSS"]
        )

        base_df = st.session_state.data[["Date", "TSS"]].copy()
        base_df = pd.concat([base_df, new_row], ignore_index=True)

        st.session_state.data = recalc_ctl(base_df)
        st.session_state.data.to_csv(FILE_NAME, index=False)

        st.success("保存しました")

    st.divider()

    st.subheader("データ一覧")

    if not st.session_state.data.empty:

        df_display = (
            st.session_state.data[
                st.session_state.data["TSS"] > 0
            ]
            .copy()
            .reset_index(drop=True)
        )

        if not df_display.empty:

            df_display[["CTL", "ATL", "TSB"]] = (
                df_display[["CTL", "ATL", "TSB"]].round(2)
            )

            selected_index = st.selectbox(
                "削除する日付",
                df_display.index,
                format_func=lambda x:
                    f"{df_display.loc[x,'Date'].date()} | TSS={df_display.loc[x,'TSS']}"
            )

            if st.button("削除"):

                delete_date = df_display.loc[selected_index, "Date"]

                base_df = st.session_state.data[["Date", "TSS"]].copy()
                base_df = base_df[base_df["Date"] != delete_date]

                st.session_state.data = recalc_ctl(base_df)
                st.session_state.data.to_csv(FILE_NAME, index=False)

                st.success("削除しました")

            st.dataframe(df_display, use_container_width=True)

        else:
            st.info("表示できるデータがありません")

# ==========================
# 右列：グラフ
# ==========================
with right_col:

    if not st.session_state.data.empty:

        st.subheader("推移グラフ")

        df_chart = st.session_state.data.sort_values("Date")

        mode = st.radio(
            "表示期間",
            ["全期間", "期間指定"],
            horizontal=True
        )

        if mode == "全期間":
            df_filtered = df_chart
        else:
            min_date = df_chart["Date"].min()
            max_date = df_chart["Date"].max()

            col1, col2 = st.columns(2)

            with col1:
                start_date = st.date_input(
                    "開始日",
                    value=min_date,
                    min_value=min_date,
                    max_value=max_date
                )

            with col2:
                end_date = st.date_input(
                    "終了日",
                    value=max_date,
                    min_value=min_date,
                    max_value=max_date
                )

            if start_date > end_date:
                st.warning("開始日は終了日より前にしてください")
                st.stop()

            df_filtered = df_chart[
                (df_chart["Date"] >= pd.to_datetime(start_date)) &
                (df_chart["Date"] <= pd.to_datetime(end_date))
            ]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df_filtered["Date"],
            y=df_filtered["CTL"],
            mode="lines",
            name="CTL",
            hovertemplate="CTL: %{y:.3f}<extra></extra>"
        ))

        fig.add_trace(go.Scatter(
            x=df_filtered["Date"],
            y=df_filtered["ATL"],
            mode="lines",
            name="ATL",
            hovertemplate="ATL: %{y:.3f}<extra></extra>"
        ))

        fig.add_trace(go.Scatter(
            x=df_filtered["Date"],
            y=df_filtered["TSB"],
            mode="lines",
            name="TSB",
            hovertemplate="TSB: %{y:.3f}<extra></extra>"
        ))

        fig.update_layout(
            hovermode="x unified",
            xaxis_title="Date",
            yaxis_title="Value",
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)