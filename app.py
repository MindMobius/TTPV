import gradio as gr
import os
import pyttsx3
import subprocess
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# 全局变量
avatars = []
voices = []
default_avatar = None

def parse_script(text):
    """解析脚本格式文本 '角色::文本' 到列表"""
    if not text or text.strip() == "":
        return [["1", "", ""]]
        
    lines = text.strip().split('\n')
    results = []
    for i, line in enumerate(lines, 1):
        if '::' in line:
            char, content = line.split('::', 1)
            results.append([str(i), char.strip(), content.strip()])
    return results if results else [["1", "", ""]]

def get_unique_characters(data):
    """从文稿中提取唯一角色列表"""
    if data is None or (hasattr(data, 'empty') and data.empty):
        return []
    if hasattr(data, 'values'):
        data = data.values.tolist()
    elif not isinstance(data, list):
        data = data.tolist()
    chars = {row[1] for row in data if row[1].strip()}
    return sorted(list(chars))

def get_default_tts_config(char, voices):
    """获取角色的默认TTS配置"""
    return [char, voices[0].name if voices else "", 200, 1.0]

def update_tts_configs(data, existing_configs, voices):
    """更新TTS配置列表，为新角色创建默认配置"""
    chars = get_unique_characters(data)
    configs = []
    old_configs = {}
    if existing_configs is not None:
        if hasattr(existing_configs, 'values'):
            old_list = existing_configs.values.tolist()
        elif not isinstance(existing_configs, list):
            old_list = existing_configs.tolist()
        else:
            old_list = existing_configs
        old_configs = {config[0]: config for config in old_list if config[0].strip()}
    
    for char in chars:
        if char in old_configs:
            configs.append(old_configs[char])
        else:
            configs.append(get_default_tts_config(char, voices))
    return configs

def load_char_config(char, configs):
    """加载角色配置"""
    global default_avatar
    
    if configs is None or len(configs) == 0 or not char:
        return [voices[0].name if voices else "", 200, 1.0, "", default_avatar, f"assets/avatar/{default_avatar}"]
            
    if hasattr(configs, 'values'):
        configs = configs.values.tolist()
            
    for config in configs:
        if config[0] == char:
            # 确保立绘在可选列表中
            avatar_name = config[4] if config[4] and config[4] in avatars else default_avatar
            avatar_path = f"assets/avatar/{avatar_name}" if avatar_name else None
            return config[1:4] + ["点击预览", avatar_name, avatar_path]
                
    return [voices[0].name if voices else "", 200, 1.0, "", default_avatar, f"assets/avatar/{default_avatar}"]

def get_asset_files(folder):
    """获取指定文件夹下的所有文件"""
    path = Path(folder)
    if not path.exists():
        return []
    return [f.name for f in path.glob('*') if f.is_file()]

def generate_video(script_data, tts_configs, background):
    """生成视频"""
    if hasattr(script_data, 'values'):
        data = script_data.values.tolist()
    elif not isinstance(script_data, list):
        data = script_data.tolist()
    else:
        data = script_data
        
    if not data:
        return "没有台词数据"
        
    if not background:
        return "请选择背景图片"
        
    width, height = 1280, 720
    fps = 30
    font_color = (255, 255, 255)
    
    bg_path = f'assets/background/{background}'
    
    Path("movies").mkdir(parents=True, exist_ok=True)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_path = 'movies/scene.mp4'
    out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
    
    if not out.isOpened():
        return "视频写入器初始化失败"
    
    try:
        bg = cv2.imread(bg_path)
        if bg is None:
            return f"背景图片加载失败: {bg_path}"
        bg = cv2.resize(bg, (width, height))
        
        # 创建角色立绘字典
        avatars_dict = {}
        if hasattr(tts_configs, 'values'):
            configs = tts_configs.values.tolist()
        else:
            configs = tts_configs
            
        for config in configs:
            if config[4]:  # 如果有立绘配置
                char_name = config[0]
                avatar_file = config[4]
                avatar_path = f'assets/avatar/{avatar_file}'
                avatar = cv2.imread(avatar_path, cv2.IMREAD_UNCHANGED)
                if avatar is not None:
                    avatar_height = int(height * 0.8)
                    aspect_ratio = avatar.shape[1] / avatar.shape[0]
                    avatar_width = int(avatar_height * aspect_ratio)
                    avatars_dict[char_name] = cv2.resize(avatar, (avatar_width, avatar_height))
        
        for line in data:
            if len(line) < 3 or not line[1].strip():
                continue
                
            char_name = line[1]
            text = line[2]
            
            frame = bg.copy()
            
            # 使用对应角色的立绘
            if char_name in avatars_dict:
                avatar = avatars_dict[char_name]
                avatar_x = 50
                avatar_y = height - avatar.shape[0]
                
                if avatar.shape[2] == 4:
                    alpha = avatar[:, :, 3] / 255.0
                    for c in range(3):
                        frame[avatar_y:avatar_y+avatar.shape[0], 
                              avatar_x:avatar_x+avatar.shape[1], c] = \
                            frame[avatar_y:avatar_y+avatar.shape[0], 
                                  avatar_x:avatar_x+avatar.shape[1], c] * (1-alpha) + \
                            avatar[:, :, c] * alpha
                else:
                    frame[avatar_y:avatar_y+avatar.shape[0], 
                          avatar_x:avatar_x+avatar.shape[1]] = avatar[:, :, :3]
            
            overlay = frame.copy()
            cv2.rectangle(overlay, (50, height-150), (width-50, height-50), (0,0,0), -1)
            frame = cv2.addWeighted(overlay, 0.5, frame, 0.5, 0)
            
            pil_im = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_im)
            
            name_font = ImageFont.truetype('assets/fonts/AlibabaPuHuiTi-3-55-Regular.ttf', 36)
            text_font = ImageFont.truetype('assets/fonts/AlibabaPuHuiTi-3-55-Regular.ttf', 32)
            draw.text((70, height-120), char_name, font=name_font, fill=font_color)
            draw.text((70, height-80), text, font=text_font, fill=font_color)
            
            frame = cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)
            
            for _ in range(int(fps * 2)):
                out.write(frame)
                
        out.release()
        
        if not Path(video_path).exists():
            return "视频文件未生成"
        if Path(video_path).stat().st_size == 0:
            return "视频文件大小为0"
            
        return f"视频已生成: {video_path}"
        
    except Exception as e:
        return f"生成失败: {str(e)}"
    finally:
        if out.isOpened():
            out.release()

def create_interface():
    global avatars, voices, default_avatar
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    avatars = get_asset_files('assets/avatar')
    backgrounds = get_asset_files('assets/background')
    
    # 设置默认值
    default_background = backgrounds[0] if backgrounds else None
    default_avatar = "avatar_1.png" if "avatar_1.png" in avatars else avatars[0] if avatars else None

    def preview_tts(char, voice_name, rate, volume, text):
        if not char or not voice_name:
            return
        
        engine = pyttsx3.init()
        for voice in voices:
            if voice.name == voice_name:
                engine.setProperty('voice', voice.id)
                break
        engine.setProperty('rate', int(rate))
        engine.setProperty('volume', float(volume))
        engine.say(text)
        engine.runAndWait()
        
    def update_char_list(data):
        chars = get_unique_characters(data)
        return gr.update(choices=chars)
    
    def save_char_config(char, voice, rate, volume, avatar, existing_configs):
        if not char:
            return existing_configs
        
        if hasattr(existing_configs, 'values'):
            configs = existing_configs.values.tolist()
        else:
            configs = existing_configs if existing_configs else []
        
        updated = False
        for i, config in enumerate(configs):
            if config[0] == char:
                configs[i] = [char, voice, rate, volume, avatar]
                updated = True
                break
        
        if not updated:
            configs.append([char, voice, rate, volume, avatar])
        
        return configs

    with gr.Blocks(css="footer {display: none} .wrap {word-break: break-all;}") as demo:
        gr.Markdown("# TTPV - 文本生成像素视频")
        
        # 1. 文本输入面板
        with gr.Row():
            with gr.Column():
                script_input = gr.Textbox(
                    label="脚本输入 (格式: 角色::文本)", 
                    lines=3,
                    placeholder="爱丽丝::你好啊\n鲍勃::你也好",
                    value="爱丽丝::今天天气真好呢\n鲍勃::是啊，很适合出去玩\n爱丽丝::那我们去公园吧"
                )
                parse_btn = gr.Button("解析脚本")
                script_table = gr.Dataframe(
                    headers=["#", "角色", "台词"],
                    datatype=["str", "str", "str"],
                    col_count=(3, "fixed"),
                    interactive=True,
                    value=[["1", "", ""]],
                    wrap=True
                )
                add_row_btn = gr.Button("添加行")

        # 2. 角色配置表
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 角色配置")
                char_config_table = gr.Dataframe(
                    headers=["角色", "音色", "语速", "音量", "立绘"],
                    datatype=["str", "str", "number", "number", "str"],
                    col_count=(5, "fixed"),
                    interactive=False,
                    value=[],
                    wrap=True
                )

        # 3. 角色控制面板
        with gr.Row():
            # 左侧立绘预览和选择
            with gr.Column(scale=1):
                avatar_preview = gr.Image(
                    label="立绘预览",
                    type="filepath",
                    height=300
                )
                avatar_select = gr.Dropdown(
                    label="选择立绘",
                    choices=avatars,
                    value=avatars[0] if avatars else None,
                    interactive=True
                )
            
            # 右侧角色配置
            with gr.Column(scale=2):
                gr.Markdown("### 角色控制")
                with gr.Row():
                    char_select = gr.Dropdown(
                        label="选择角色",
                        choices=[],
                        interactive=True
                    )
                    voice_select = gr.Dropdown(
                        label="音色",
                        choices=[v.name for v in voices],
                        value=voices[0].name if voices else None,
                        interactive=True
                    )
                with gr.Row():
                    rate = gr.Slider(
                        label="语速",
                        minimum=50,
                        maximum=300,
                        value=200,
                        step=10,
                        interactive=True
                    )
                    volume = gr.Slider(
                        label="音量",
                        minimum=0,
                        maximum=1,
                        value=1,
                        step=0.1,
                        interactive=True
                    )
                with gr.Row():
                    preview_text = gr.Textbox(
                        label="预览文本",
                        value="点击预览",
                        interactive=True
                    )
                    preview_btn = gr.Button("预览")
                    save_config_btn = gr.Button("保存配置")

        # 4. 视频控制面板
        with gr.Row():
            # 左侧背景预览
            with gr.Column(scale=1):
                background_preview = gr.Image(
                    label="背景预览",
                    type="filepath",
                    value=f"assets/background/{default_background}" if default_background else None,
                    height=300
                )
            # 右侧控制
            with gr.Column(scale=2):
                gr.Markdown("### 视频控制")
                background_select = gr.Dropdown(
                    label="选择背景",
                    choices=backgrounds,
                    value=default_background,
                    allow_custom_value=False,
                    interactive=True
                )
                generate_btn = gr.Button("生成视频", variant="primary")
                output = gr.Textbox(label="输出信息")

        # 更新立绘预览
        def update_avatar_preview(avatar_name):
            if not avatar_name:
                return None
            return f"assets/avatar/{avatar_name}"
            
        avatar_select.change(
            fn=update_avatar_preview,
            inputs=[avatar_select],
            outputs=[avatar_preview]
        )

        # 更新解析脚本事件
        parse_btn.click(
            fn=lambda x: (
                parse_script(x),
                gr.update(choices=get_unique_characters(parse_script(x)), 
                         value=get_unique_characters(parse_script(x))[0] if get_unique_characters(parse_script(x)) else None),
                [[char, voices[0].name if voices else "", 200, 1.0, default_avatar] 
                 for char in get_unique_characters(parse_script(x))],
                gr.update(value=voices[0].name if voices else ""),
                gr.update(value=200),
                gr.update(value=1.0),
                gr.update(value="点击预览"),
                gr.update(value=default_avatar),
                gr.update(value=f"assets/avatar/{default_avatar}" if default_avatar else None)
            ),
            inputs=[script_input],
            outputs=[
                script_table, 
                char_select, 
                char_config_table,
                voice_select,
                rate,
                volume,
                preview_text,
                avatar_select,
                avatar_preview
            ]
        )

        char_select.change(
            fn=load_char_config,
            inputs=[char_select, char_config_table],
            outputs=[voice_select, rate, volume, preview_text, avatar_select, avatar_preview]
        )

        save_config_btn.click(
            fn=save_char_config,
            inputs=[char_select, voice_select, rate, volume, avatar_select, char_config_table],
            outputs=[char_config_table]
        )

        preview_btn.click(
            fn=preview_tts,
            inputs=[char_select, voice_select, rate, volume, preview_text]
        )

        # 更新生成视频事件
        generate_btn.click(
            fn=generate_video,
            inputs=[script_table, char_config_table, background_select],
            outputs=[output]
        )

        # 更新背景预览
        def update_background_preview(background_name):
            if not background_name:
                return None
            return f"assets/background/{background_name}"
            
        background_select.change(
            fn=update_background_preview,
            inputs=[background_select],
            outputs=[background_preview]
        )

    return demo

if __name__ == "__main__":
    demo = create_interface()
    demo.launch(inbrowser=True) 