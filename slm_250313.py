
 
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from flask import Flask
from shotgun_api3 import Shotgun

# Flaskアプリケーションの初期化
server = Flask(__name__)

# Dashアプリケーションの初期化
app = dash.Dash(__name__, server=server, url_base_pathname='/')

# ShotGridのURLと認証情報
SERVER_PATH = "https://voxel.shotgunstudio.com"
SCRIPT_NAME = "Sawada_test"
SCRIPT_KEY = "hq#tmmonoui1pkvIabqzyqiiz"

# ShotGrid APIクライアントの作成
sg = Shotgun(SERVER_PATH, SCRIPT_NAME, SCRIPT_KEY)

# プロジェクトIDを設定
project_id = 3711  # 変更後のプロジェクトID

# ショットごとのタスクデータを取得する関数
def get_task_data_by_shot(shot_id):
    filters = [
        ['project', 'is', {'type': 'Project', 'id': project_id}],
        ['entity', 'is', {'type': 'Shot', 'id': shot_id}]
    ]
    fields = ['content', 'est_in_mins', 'time_logs_sum', 'sg_status_list']
    tasks = sg.find('Task', filters, fields)
    return tasks

# エピソードごとのショットデータを取得する関数
def get_shots_by_episode(episode_id):
    filters = [
        ['project', 'is', {'type': 'Project', 'id': project_id}],
        ['sg_episode', 'is', {'type': 'Episode', 'id': episode_id}]
    ]
    fields = ['id', 'code']
    shots = sg.find('Shot', filters, fields)
    return shots

# Assetごとのタスクデータを取得する関数
def get_task_data_by_asset(asset_id):
    filters = [
        ['project', 'is', {'type': 'Project', 'id': project_id}],
        ['entity', 'is', {'type': 'Asset', 'id': asset_id}]
    ]
    fields = ['content', 'est_in_mins', 'time_logs_sum', 'sg_status_list']
    tasks = sg.find('Task', filters, fields)
    return tasks

# Assetのリストを取得
assets = sg.find('Asset', [['project', 'is', {'type': 'Project', 'id': project_id}]], ['id', 'code'])

# エピソードのリストを取得
episodes = sg.find('Episode', [['project', 'is', {'type': 'Project', 'id': project_id}]], ['id', 'code'])

# Debug: エピソードとAssetのリストを表示
print("Episodes:", episodes)
print("Assets:", assets)

# Dashアプリケーションのレイアウト
app.layout = html.Div([
    dcc.Tabs(id="tabs-example", value='tab-all-episodes', children=[
        dcc.Tab(label='全エピソード', value='tab-all-episodes'),
        *[dcc.Tab(label=episode['code'], value=f"tab-episode-{episode['id']}") for episode in episodes],
        *[dcc.Tab(label=asset['code'], value=f"tab-asset-{asset['id']}") for asset in assets]
    ], style={'overflow': 'auto', 'white-space': 'normal'}),
    html.Div(id='tabs-content-example')
])

# タブのコールバック
@app.callback(
    Output('tabs-content-example', 'children'),
    Input('tabs-example', 'value')
)
def render_content(tab):
    try:
        print(f"Selected tab: {tab}")  # デバッグ用出力
        tasks = []
        if tab == 'tab-all-episodes':
            tasks = sg.find('Task', [['project', 'is', {'type': 'Project', 'id': project_id}]], ['content', 'est_in_mins', 'time_logs_sum', 'sg_status_list'])
        elif tab.startswith('tab-episode-'):
            episode_id = int(tab.split('-')[-1])
            shots = get_shots_by_episode(episode_id)
            for shot in shots:
                shot_tasks = get_task_data_by_shot(shot['id'])
                tasks.extend(shot_tasks)
        elif tab.startswith('tab-asset-'):
            asset_id = int(tab.split('-')[-1])
            tasks = get_task_data_by_asset(asset_id)

        # Debug: 取得したタスクデータを表示
        print(f"Tasks: {tasks}")

        # データをフィルタリングし整形
        filtered_tasks = [task for task in tasks if task['est_in_mins'] is not None]
        filtered_tasks.sort(key=lambda x: x['content'])  # タスク名でソート

        task_names = [f"{task['content']} ⚫️" if task['sg_status_list'] == 'fin' else task['content'] for task in filtered_tasks]
        bids = [task['est_in_mins'] / 60 / 8 for task in filtered_tasks]  # 分 -> 時間 -> 日
        time_logged = [task['time_logs_sum'] / 60 / 8 if task['time_logs_sum'] is not None else 0 for task in filtered_tasks]  # 分 -> 時間 -> 日

        # トータルの予定日数と実際の日数を計算
        total_bids = sum(bids)
        total_time_logged = sum(time_logged)

        # サブプロットの作成
        fig = make_subplots(
            rows=3, cols=1,
            row_heights=[0.6, 0.2, 0.2],
            specs=[[{"type": "xy"}], [{"type": "domain"}], [{"type": "xy"}]],  # 円グラフの下に棒グラフを追加
            vertical_spacing=0.05,  # グラフ間のスペースを縮める
            subplot_titles=("タスクの予定日数と実際の日数 (8時間 = 1日)", "トータルの予定日数と実際の日数", "トータルの比較")
        )

        # 棒グラフを作成（タスクごと）
        fig.add_trace(go.Bar(
            y=task_names,
            x=bids,
            name='予定日数',
            orientation='h',
            marker=dict(color='blue')
        ), row=1, col=1)

        fig.add_trace(go.Bar(
            y=task_names,
            x=time_logged,
            name='実際の日数',
            orientation='h',
            marker=dict(color='orange')
        ), row=1, col=1)

        # 円グラフを作成（トータル）
        labels = ['予定日数', '実際の日数']
        values = [total_bids, total_time_logged]

        fig.add_trace(go.Pie(
            labels=labels,
            values=values,
            hole=.3
        ), row=2, col=1)

        # トータルの棒グラフを作成
        fig.add_trace(go.Bar(
            x=['見積', '予定日数', '実際の日数'],
            y=[61.8, total_bids, total_time_logged],
            name='トータル比較',
            text=[f"資料収集、検証、MTG: 5\nディレクション: 3\n管理費: 5.8\n作業工数: 48", '', ''],
            textposition='inside',
            marker=dict(color=['green', 'blue', 'orange'])
        ), row=3, col=1)

        # グラフのレイアウトを設定
        fig.update_layout(
            height=1000 + (50 * len(task_names)),  # グラフの高さを調整
            margin=dict(l=200, r=20, t=50, b=20),  # 左の余白を広げる
            barmode='group'
        )

        return dcc.Graph(figure=fig)
    except Exception as e:
        print(f"Error: {e}")  # エラーメッセージを表示
        return html.Div([html.H3(f"Error: {e}")])

# Flaskアプリケーションの実行
if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8080)






 