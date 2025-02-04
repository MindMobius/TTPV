import gradio as gr
import os
import pyttsx3

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
    if not data or len(data) == 0:
        return []
    # 处理数据类型
    if hasattr(data, 'values'):
        data = data.values.tolist()
    elif not isinstance(data, list):
        data = data.tolist()
    # 提取第2列(角色名)并去重
    chars = {row[1] for row in data if row[1].strip()}
    return sorted(list(chars))

def get_default_tts_config(char, voices):
    """获取角色的默认TTS配置"""
    return [char, voices[0].name if voices else "", 200, 1.0]

def update_tts_configs(data, existing_configs, voices):
    """更新TTS配置列表，为新角色创建默认配置"""
    chars = get_unique_characters(data)
    configs = []  # 创建新的空列表
    
    # 获取现有配置
    old_configs = {}
    if existing_configs is not None:
        if hasattr(existing_configs, 'values'):
            old_list = existing_configs.values.tolist()
        elif not isinstance(existing_configs, list):
            old_list = existing_configs.tolist()
        else:
            old_list = existing_configs
        # 转换为字典以便快速查找
        old_configs = {config[0]: config for config in old_list if config[0].strip()}
    
    # 为每个角色创建或保留配置
    for char in chars:
        if char in old_configs:
            configs.append(old_configs[char])  # 保留现有配置
        else:
            configs.append(get_default_tts_config(char, voices))  # 创建新配置
            
    return configs

def load_char_config(char, configs):
    """加载指定角色的TTS配置"""
    if configs is None or len(configs) == 0 or not char:
        return None, None, None, None
        
    # DataFrame转换为list处理
    if hasattr(configs, 'values'):
        configs = configs.values.tolist()
    elif not isinstance(configs, list):
        configs = configs.tolist()
    
    for config in configs:
        if config[0] == char:
            return config[1], config[2], config[3], "点击预览"
    return None, None, None, None

def create_interface():
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    
    with gr.Blocks(css="footer {display: none} .wrap {word-break: break-all;}") as demo:
        gr.Markdown("# TTPV - 文本生成像素视频")
        
        with gr.Row():
            # 左侧输入区
            with gr.Column(scale=1):
                script_input = gr.Textbox(
                    label="脚本输入 (格式: 角色::文本)", 
                    lines=3,
                    placeholder="爱丽丝::你好啊\n鲍勃::你也好",
                    value="爱丽丝::今天天气真好呢\n鲍勃::是啊，很适合出去玩\n爱丽丝::那我们去公园吧"
                )
                parse_btn = gr.Button("解析脚本")
                
            # 右侧编辑区
            with gr.Column(scale=2):
                # TTS控制区
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
                    preview_text = gr.Textbox(
                        label="预览文本",
                        value="点击预览",
                        interactive=True
                    )
                    preview_btn = gr.Button("预览")
                    save_btn = gr.Button("保存配置")

                # 角色TTS配置列表
                tts_configs = gr.Dataframe(
                    headers=["角色", "音色", "语速", "音量"],
                    datatype=["str", "str", "number", "number"],
                    col_count=(4, "fixed"),
                    interactive=False,
                    value=[],
                    wrap=True,
                    column_widths=["150px", "200px", "100px", "100px"]
                )

                # 文稿编辑区
                script_table = gr.Dataframe(
                    headers=["#", "角色", "台词"],
                    datatype=["str", "str", "str"],
                    col_count=(3, "fixed"),
                    interactive=True,
                    value=[["1", "", ""]],
                    wrap=True,
                    column_widths=["50px", "150px", "auto"]
                )
                add_row_btn = gr.Button("添加行")

        # 预览TTS
        def preview_tts(char, voice_name, rate, volume, text):
            if not char or not voice_name:
                return
            
            engine = pyttsx3.init()
            # 找到对应的voice
            for voice in voices:
                if voice.name == voice_name:
                    engine.setProperty('voice', voice.id)
                    break
                    
            engine.setProperty('rate', int(rate))
            engine.setProperty('volume', float(volume))
            engine.say(text)
            engine.runAndWait()

        # 更新角色列表
        def update_char_list(data):
            chars = get_unique_characters(data)
            return gr.Dropdown(choices=chars)

        # 当选择角色时加载配置
        def on_char_select(char, configs):
            voice, rate, volume, preview = load_char_config(char, configs)
            return voice, rate, volume, preview
            
        char_select.change(
            fn=on_char_select,
            inputs=[char_select, tts_configs],
            outputs=[voice_select, rate, volume, preview_text]
        )

        # 更新解析脚本事件
        parse_btn.click(
            fn=lambda x, y, z: (
                parse_script(x),  # 解析脚本
                update_char_list(parse_script(x)),  # 更新角色下拉列表
                update_tts_configs(parse_script(x), z, voices)  # 更新TTS配置
            ),
            inputs=[script_input, script_table, tts_configs],
            outputs=[script_table, char_select, tts_configs]
        )

        def add_empty_row(data):
            if data is None or len(data) == 0:
                return [["1", "", ""]]
            if hasattr(data, 'values'):
                data = data.values.tolist()
            elif not isinstance(data, list):
                data = data.tolist()
            next_num = str(len(data) + 1)
            data.append([next_num, "", ""])
            return data

        add_row_btn.click(
            fn=add_empty_row,
            inputs=[script_table],
            outputs=[script_table]
        )

        # 保存(更新)TTS配置
        def save_tts_config(char, voice, rate, volume, existing_configs):
            if not char:
                return existing_configs
            
            if hasattr(existing_configs, 'values'):
                configs = existing_configs.values.tolist()
            elif not isinstance(existing_configs, list):
                configs = existing_configs.tolist() if existing_configs is not None else []
            else:
                configs = existing_configs if existing_configs else []
            
            # 更新配置
            for i, config in enumerate(configs):
                if config[0] == char:
                    configs[i] = [char, voice, rate, volume]
                    break
                    
            return configs

        save_btn.click(
            fn=save_tts_config,
            inputs=[char_select, voice_select, rate, volume, tts_configs],
            outputs=[tts_configs]
        )

        # 事件处理
        preview_btn.click(
            fn=preview_tts,
            inputs=[char_select, voice_select, rate, volume, preview_text]
        )

    return demo

if __name__ == "__main__":
    demo = create_interface()
    demo.launch(inbrowser=True)  # 自动打开浏览器 