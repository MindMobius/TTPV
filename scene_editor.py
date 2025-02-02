import pygame
import pygame_gui
import os
from pathlib import Path
import math
import random

class SceneEditor:
    def __init__(self):
        pygame.init()
        self.window_size = (800, 600)
        self.window = pygame.display.set_mode(self.window_size)
        pygame.display.set_caption("TTPV Scene Editor")
        
        self.manager = pygame_gui.UIManager(self.window_size)
        
        # 资源路径
        self.assets_path = Path("assets")
        self.avatar_path = self.assets_path / "avatar"
        self.bg_path = self.assets_path / "background"
        
        # 场景状态
        self.background = None
        self.avatars = []  # [(surface, rect, selected), ...]
        self.characters = []  # 存储 CharacterSprite 实例
        self.selected_avatar = None
        self.selected_character_index = None
        
        # 资源选择对话框
        self.resource_dialog = None
        self.resource_type = None  # 'avatar' 或 'background'
        self.grid_container = None
        
        # 动作选单
        self.action_menu = None
        self.actions = [
            ('Wave', 'wave'),
            ('Smile', 'smile'),
            ('Nod', 'nod')
        ]
        
        # 添加表情
        self.emotion = None
        self.emotion_timer = 0
        self.emotion_surface = None
        
        self._init_ui()
        self._load_default_background()
    
    def _init_ui(self):
        # 更换背景按钮移到右上角
        self.change_bg_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(self.window_size[0] - 110, 10, 100, 30),
            text="Change BG",
            manager=self.manager
        )
        
        # 角色列表区域
        self.avatar_list_rect = pygame.Rect(10, 10, 120, self.window_size[1] - 20)
        self.avatar_buttons = []  # 存储角色按钮和删除按钮的列表 [(avatar_btn, delete_btn), ...]
        
        # 添加角色按钮（加号）
        self._update_add_avatar_button()
    
    def _update_add_avatar_button(self):
        # 删除旧的加号按钮（如果存在）
        if hasattr(self, 'add_avatar_button'):
            self.add_avatar_button.kill()
        
        # 只在角色数量未达到上限时显示加号按钮
        if len(self.avatars) < 4:  # 修改为4个角色上限
            # 计算新按钮位置
            y_pos = 10 + len(self.avatar_buttons) * 130
            self.add_avatar_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(10, y_pos, 120, 120),
                text="+",
                manager=self.manager
            )
    
    def _load_default_background(self):
        # 加载第一个找到的背景图片
        bg_files = list(self.bg_path.glob('*.jpg')) + list(self.bg_path.glob('*.jpg'))
        if bg_files:
            self.background = pygame.image.load(str(bg_files[0]))
            self.background = pygame.transform.scale(self.background, self.window_size)
    
    def add_avatar(self, avatar_file):
        if len(self.avatars) >= 4:
            return
            
        avatar_path = self.avatar_path / avatar_file
        if avatar_path.exists():
            # 加载角色图片
            surface = pygame.image.load(str(avatar_path))
            surface = pygame.transform.scale(surface, (100, 100))
            rect = surface.get_rect(center=(400, 300))
            self.avatars.append([surface, rect, False])
            
            # 创建角色精灵
            character = CharacterSprite(str(avatar_path))
            self.characters.append(character)
            
            # 创建UI按钮
            y_pos = 10 + len(self.avatar_buttons) * 130
            avatar_btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(10, y_pos, 120, 120),
                text="",
                manager=self.manager
            )
            
            # 设置预览图片
            preview_surface = pygame.transform.scale(surface, (120, 120))
            avatar_btn.normal_image = preview_surface
            avatar_btn.hovered_image = preview_surface
            avatar_btn.selected_image = preview_surface
            avatar_btn.rebuild()
            
            # 创建删除按钮
            delete_btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(100, y_pos, 20, 20),
                text="×",
                manager=self.manager
            )
            
            self.avatar_buttons.append((avatar_btn, delete_btn))
            self._update_add_avatar_button()
    
    def _create_resource_dialog(self, resource_type):
        self.resource_type = resource_type
        dialog_size = (400, 300)
        
        self.resource_dialog = pygame_gui.elements.UIWindow(
            rect=pygame.Rect((self.window_size[0] - dialog_size[0]) // 2,
                           (self.window_size[1] - dialog_size[1]) // 2,
                           *dialog_size),
            window_display_title="Select Resource",
            manager=self.manager
        )
        
        container = pygame_gui.elements.UIScrollingContainer(
            relative_rect=pygame.Rect(0, 0, 380, 240),
            manager=self.manager,
            container=self.resource_dialog
        )
        
        path = self.avatar_path if resource_type == 'avatar' else self.bg_path
        files = list(path.glob('*.png')) + list(path.glob('*.jpg'))
        
        btn_size = (80, 80)
        margin = 10
        cols = 4
        row = 0
        col = 0
        
        for file in files:
            btn_rect = pygame.Rect(
                col * (btn_size[0] + margin),
                row * (btn_size[1] + margin),
                *btn_size
            )
            
            # 创建图片预览
            image_surface = pygame.image.load(str(file))
            image_surface = pygame.transform.scale(image_surface, btn_size)
            
            # 只使用文件名部分（不含后缀）作为 object_id
            name_without_ext = file.stem
            
            # 创建按钮并设置图片
            btn = pygame_gui.elements.UIButton(
                relative_rect=btn_rect,
                text="",
                manager=self.manager,
                container=container,
                object_id=f'#resource_{name_without_ext}'
            )
            
            # 存储完整文件名作为按钮的自定义属性
            setattr(btn, 'original_file', file.name)  # 使用 setattr 确保属性被正确设置
            
            # 将图片设置为按钮背景
            btn.normal_image = image_surface
            btn.hovered_image = image_surface
            btn.selected_image = image_surface
            btn.rebuild()
            
            col += 1
            if col >= cols:
                col = 0
                row += 1
        
        total_height = (row + (1 if col > 0 else 0)) * (btn_size[1] + margin)
        container.set_scrollable_area_dimensions((380, total_height))

    def _create_action_menu(self, character_index):
        # 如果已有菜单，先关闭
        if self.action_menu:
            self.action_menu.kill()
        
        # 获取对应角色按钮的位置
        btn_rect = self.avatar_buttons[character_index][0].rect
        
        # 创建动作菜单窗口 - 增加宽度确保内容完整显示
        menu_width = len(self.actions) * 95 + 100  # 动作按钮宽度
        menu_height = 45 + 150  # 调节面板高度
        
        # 确保菜单不会超出窗口右边界
        menu_x = min(btn_rect.right + 10, self.window_size[0] - menu_width)
        
        self.action_menu = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(menu_x, btn_rect.top,
                            menu_width, menu_height),
            window_display_title="Actions",
            manager=self.manager
        )
        
        # 添加动作按钮 - 横向排列
        for i, (action_name, action_id) in enumerate(self.actions):
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(5 + i * 95, 5, 90, 30),
                text=action_name,
                manager=self.manager,
                container=self.action_menu,
                object_id=f"@action_{action_id}"
            )
        
        # 添加调节面板
        panel_rect = pygame.Rect(5, 45, menu_width - 10, 140)
        
        # 头部位置调节
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(5, 45, 80, 20),
            text="Head Pos:",
            manager=self.manager,
            container=self.action_menu
        )
        
        # X位置滑块
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(85, 45, 20, 20),
            text="X:",
            manager=self.manager,
            container=self.action_menu
        )
        head_x_slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect(105, 45, 100, 20),
            start_value=self.characters[character_index].parts['head']['pos'][0],
            value_range=(-50, 50),
            manager=self.manager,
            container=self.action_menu,
            object_id=f"@slider_head_x"
        )
        
        # Y位置滑块
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(215, 45, 20, 20),
            text="Y:",
            manager=self.manager,
            container=self.action_menu
        )
        head_y_slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect(235, 45, 100, 20),
            start_value=self.characters[character_index].parts['head']['pos'][1],
            value_range=(-100, 0),
            manager=self.manager,
            container=self.action_menu,
            object_id=f"@slider_head_y"
        )
        
        # 头部大小调节
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(5, 75, 80, 20),
            text="Head Size:",
            manager=self.manager,
            container=self.action_menu
        )
        head_size_slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect(85, 75, 250, 20),
            start_value=self.characters[character_index].head.get_width(),
            value_range=(40, 120),
            manager=self.manager,
            container=self.action_menu,
            object_id=f"@slider_head_size"
        )
        
        # 姿势选择
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(5, 105, 80, 20),
            text="Pose:",
            manager=self.manager,
            container=self.action_menu
        )
        
        # 姿势按钮
        poses = [("Stand", "stand"), ("Pose 1", "pose1"), ("Pose 2", "pose2")]
        for i, (pose_name, pose_id) in enumerate(poses):
            pose_btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(85 + i * 95, 105, 90, 20),
                text=pose_name,
                manager=self.manager,
                container=self.action_menu,
                object_id=f"@pose_{pose_id}"
            )

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            print(f"Button pressed: {event.ui_element.object_ids}")  # 调试所有按钮点击
            
            # 检查是否点击了删除按钮
            for i, (avatar_btn, delete_btn) in enumerate(self.avatar_buttons):
                if event.ui_element == delete_btn:
                    # 删除对应的角色和精灵
                    self.avatars.pop(i)
                    self.characters.pop(i)
                    avatar_btn.kill()
                    delete_btn.kill()
                    self.avatar_buttons.pop(i)
                    self._rearrange_avatar_buttons()
                    break
                # 检查是否点击了角色按钮
                elif event.ui_element == avatar_btn:
                    self.selected_character_index = i
                    self._create_action_menu(i)
                    break
            
            if event.ui_element == self.add_avatar_button:
                self._create_resource_dialog('avatar')
            elif event.ui_element == self.change_bg_button:
                self._create_resource_dialog('background')
            # 检查资源按钮点击
            elif hasattr(event.ui_element, 'object_ids'):
                if any('#resource_' in id_ for id_ in event.ui_element.object_ids if id_):
                    # 确保属性存在
                    if hasattr(event.ui_element, 'original_file'):
                        resource_name = event.ui_element.original_file
                        print(f"Loading resource: {resource_name}")  # 调试输出
                        
                        if self.resource_type == 'avatar':
                            self.add_avatar(resource_name)
                        else:
                            self._load_background(resource_name)
                        self.resource_dialog.kill()
                        self.resource_dialog = None
            # 检查动作按钮点击 - 移到外面，独立的条件分支
            if hasattr(event.ui_element, 'object_ids'):
                if any('@action_' in id_ for id_ in event.ui_element.object_ids if id_):
                    print("Action button clicked!")  # 调试输出
                    if self.selected_character_index is not None:
                        # 从 object_ids 中获取动作ID
                        action_id = next(id_.replace('@action_', '') 
                                       for id_ in event.ui_element.object_ids 
                                       if id_ and '@action_' in id_)
                        print(f"Playing animation: {action_id}")  # 调试输出
                        # 执行动作
                        self.characters[self.selected_character_index].play_animation(action_id)
                        # 关闭动作菜单
                        if self.action_menu:
                            self.action_menu.kill()
                            self.action_menu = None
            # 处理姿势按钮点击
            if (hasattr(event.ui_element, 'object_ids') and 
                any('@pose_' in id_ for id_ in event.ui_element.object_ids if id_)):
                if self.selected_character_index is not None:
                    pose_id = next(id_.replace('@pose_', '') 
                                 for id_ in event.ui_element.object_ids 
                                 if id_ and '@pose_' in id_)
                    character = self.characters[self.selected_character_index]
                    if pose_id == "stand":
                        character._reset_pose()
                    elif pose_id == "pose1":
                        # 开启呼吸动画
                        character._reset_pose()  # 先重置
                        character.is_breathing = True
                    elif pose_id == "pose2":
                        # 吊儿郎当的姿势
                        character.set_pose({
                            'body': {'angle': -3},  # 身体微微后倾
                            'head': {'angle': 5},   # 头微微抬起
                            'left_arm': {'angle': -15},  # 手臂自然下垂但略微外张
                            'right_arm': {'angle': 25},  # 一只手臂更外张
                            'left_leg': {'angle': -5},   # 一条腿微微弯曲
                            'right_leg': {'angle': 10}   # 另一条腿站立
                        })
                        character.is_breathing = False  # 确保不会有呼吸动画

        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.resource_dialog:
                self.resource_dialog = None
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            for i, character in enumerate(self.characters):
                # 检查点击是否在角色区域内
                char_rect = pygame.Rect(
                    character.pos[0] - 40,  # 扩大点击区域
                    character.pos[1] - 100,
                    80,
                    200
                )
                if char_rect.collidepoint(event.pos):
                    self.selected_avatar = i
                    break
        
        if event.type == pygame.MOUSEBUTTONUP:
            self.selected_avatar = None
        
        if event.type == pygame.MOUSEMOTION:
            if self.selected_avatar is not None:
                # 更新选中角色的位置
                self.characters[self.selected_avatar].pos = list(event.pos)
                # 限制边界
                self.characters[self.selected_avatar].pos[0] = max(50, min(self.window_size[0] - 50, self.characters[self.selected_avatar].pos[0]))
                self.characters[self.selected_avatar].pos[1] = max(100, min(self.window_size[1] - 50, self.characters[self.selected_avatar].pos[1]))
        
        elif event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            if self.selected_character_index is not None:
                character = self.characters[self.selected_character_index]
                
                # 处理头部X位置滑块
                if (hasattr(event.ui_element, 'object_ids') and 
                    any('@slider_head_x' in id_ for id_ in event.ui_element.object_ids if id_)):
                    character.parts['head']['pos'][0] = event.value
                
                # 处理头部Y位置滑块
                elif (hasattr(event.ui_element, 'object_ids') and 
                      any('@slider_head_y' in id_ for id_ in event.ui_element.object_ids if id_)):
                    character.parts['head']['pos'][1] = event.value
                
                # 处理头部大小滑块
                elif (hasattr(event.ui_element, 'object_ids') and 
                      any('@slider_head_size' in id_ for id_ in event.ui_element.object_ids if id_)):
                    original_head = pygame.image.load(str(self.avatar_path / character.original_file))
                    character.head = pygame.transform.scale(original_head, (int(event.value), int(event.value)))

        self.manager.process_events(event)
    
    def _load_background(self, bg_file):
        bg_path = self.bg_path / bg_file
        if bg_path.exists():
            self.background = pygame.image.load(str(bg_path))
            self.background = pygame.transform.scale(self.background, self.window_size)
    
    def _rearrange_avatar_buttons(self):
        # 重新排列所有角色按钮
        for i, (avatar_btn, delete_btn) in enumerate(self.avatar_buttons):
            y_pos = 10 + i * 130
            avatar_btn.set_relative_position((10, y_pos))
            delete_btn.set_relative_position((100, y_pos))
        
        # 更新加号按钮位置
        self._update_add_avatar_button()
    
    def run(self):
        clock = pygame.time.Clock()
        running = True
        
        while running:
            time_delta = clock.tick(60)/1000.0
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                self.handle_event(event)
            
            # 更新角色动画
            for character in self.characters:
                character.update(time_delta * 1000)  # 转换为毫秒
            
            self.manager.update(time_delta)
            
            # 绘制
            if self.background:
                self.window.blit(self.background, (0, 0))
            
            # 绘制所有角色
            for character in self.characters:
                character.draw(self.window)
            
            self.manager.draw_ui(self.window)
            pygame.display.update()
        
        pygame.quit()

class CharacterSprite:
    def __init__(self, head_image):
        self.original_file = Path(head_image).name  # 保存原始文件名
        self.head = pygame.image.load(head_image)
        self.head = pygame.transform.scale(self.head, (70, 70))
        
        # 身体部件颜色和尺寸
        self.body_color = (60, 60, 60)
        self.sizes = {
            'body': (40, 60),
            'neck': (6, 20),
            'left_arm': (8, 50),
            'right_arm': (8, 50),
            'left_leg': (10, 60),
            'right_leg': (10, 60)
        }
        
        # 身体部件的相对位置和旋转角度
        self.parts = {
            'head': {'pos': [0, -65], 'angle': 0},
            'neck': {'pos': [0, -40], 'angle': 0},
            'body': {'pos': [0, 0], 'angle': 0},
            'left_arm': {'pos': [-20, -30], 'pivot': 'top', 'angle': 0},
            'right_arm': {'pos': [20, -30], 'pivot': 'top', 'angle': 0},
            'left_leg': {'pos': [-15, 50], 'angle': 0},
            'right_leg': {'pos': [15, 50], 'angle': 0}
        }
        
        # 基础位置
        self.pos = [400, 300]
        self.base_offset = [0, 0]
        
        # 动画系统
        self.current_animation = None
        self.animation_time = 0
        self.animation_frame = 0
        self.is_breathing = False
        self.animations = self._init_animations()
        
        # 表情系统
        self.emotion_text = None
        self.emotion_timer = 0
        self.emotion_font = pygame.font.SysFont('segoe ui emoji', 32)  # 使用系统emoji字体
    
    def _init_animations(self):
        return {
            'wave': {
                'frames': 6,  # 增加帧数使动作更流畅
                'duration': 1200,  # 增加持续时间
                'update': self._wave_update
            },
            'smile': {
                'frames': 4,
                'duration': 800,
                'update': self._smile_update
            },
            'nod': {
                'frames': 4,
                'duration': 2000,
                'update': self._nod_update
            }
        }
    
    def _wave_update(self, frame):
        # 挥手动画
        wave_angle = math.sin(frame * math.pi / 3) * 45  # 摆动幅度
        self.parts['right_arm']['angle'] = -90 + wave_angle  # 基础角度-90度（举起），然后加上摆动
        self.parts['head']['angle'] = math.sin(frame * math.pi / 3) * 5  # 轻微点头
        
        # 其他部位保持原位
        self.parts['left_arm']['angle'] = 0
        self.parts['body']['angle'] = 0
        self.parts['left_leg']['angle'] = 0
        self.parts['right_leg']['angle'] = 0
    
    def _smile_update(self, frame):
        # 抖动动画
        shake = random.randint(-2, 2)
        self.base_offset = [shake, shake]
        
        # 显示表情
        if frame == 0:
            # 使用emoji表情
            self.emotion_text = "😄"  # 也可以用 "^_^" 作为备选😃😄😁😆🤣😂😊🥰😝
            self.emotion_timer = 2000  # 显示2秒
    
    def _nod_update(self, frame):
        # 点头动画
        progress = frame / 3  # 0 到 1 的进度
        if progress <= 0.5:
            nod_amount = progress * 2
        else:
            nod_amount = (1 - progress) * 2
        
        self.parts['head']['angle'] = nod_amount * 20
        self.parts['neck']['angle'] = nod_amount * 10
    
    def draw(self, screen):
        # 计算实际绘制位置
        center_pos = (self.pos[0] + self.base_offset[0], 
                     self.pos[1] + self.base_offset[1])
        
        # 绘制身体部件
        self._draw_body_part(screen, center_pos, 'body')
        self._draw_body_part(screen, center_pos, 'neck')
        self._draw_body_part(screen, center_pos, 'left_leg')
        self._draw_body_part(screen, center_pos, 'right_leg')
        self._draw_body_part(screen, center_pos, 'left_arm')
        self._draw_body_part(screen, center_pos, 'right_arm')
        
        # 绘制头部
        head_pos = self._get_part_pos(center_pos, 'head')
        head_rotated = pygame.transform.rotate(self.head, self.parts['head']['angle'])
        head_rect = head_rotated.get_rect(center=head_pos)
        screen.blit(head_rotated, head_rect)
        
        # 绘制表情（如果有）
        if self.emotion_text and self.emotion_timer > 0:
            emotion_surface = self.emotion_font.render(self.emotion_text, True, (0, 0, 0))
            emotion_pos = (self.pos[0], self.pos[1] - 100)  # 在头顶上方显示
            screen.blit(emotion_surface, 
                       emotion_surface.get_rect(midbottom=emotion_pos))
            self.emotion_timer -= 16  # 假设60FPS
            if self.emotion_timer <= 0:
                self.emotion_text = None
    
    def _draw_body_part(self, screen, center_pos, part_name):
        if part_name not in self.sizes:
            return
            
        width, height = self.sizes[part_name]
        pos = self._get_part_pos(center_pos, part_name)
        angle = self.parts[part_name]['angle']
        
        # 创建部件表面
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(surface, self.body_color, (0, 0, width, height))
        
        # 处理手臂的特殊旋转
        if part_name in ['left_arm', 'right_arm']:
            # 设置旋转中心点在顶部
            rotated = pygame.transform.rotate(surface, angle)
            if part_name == 'left_arm':
                rect = rotated.get_rect(midtop=pos)
            else:
                rect = rotated.get_rect(midtop=pos)
        else:
            # 其他部件保持中心旋转
            rotated = pygame.transform.rotate(surface, angle)
            rect = rotated.get_rect(center=pos)
        
        screen.blit(rotated, rect)
    
    def _get_part_pos(self, center_pos, part_name):
        part = self.parts[part_name]
        angle_rad = math.radians(self.parts['body']['angle'])
        
        # 根据身体角度调整部件位置
        x = part['pos'][0] * math.cos(angle_rad) - part['pos'][1] * math.sin(angle_rad)
        y = part['pos'][0] * math.sin(angle_rad) + part['pos'][1] * math.cos(angle_rad)
        
        return (center_pos[0] + x, center_pos[1] + y)
    
    def update(self, dt):
        if self.current_animation:
            anim = self.animations[self.current_animation]
            self.animation_time += dt
            
            frame_duration = anim['duration'] / anim['frames']
            self.animation_frame = int(self.animation_time / frame_duration)
            
            if self.animation_frame < anim['frames']:
                anim['update'](self.animation_frame)
            else:
                self.current_animation = None
                self._reset_pose()
        elif self.is_breathing:  # 只在呼吸状态时更新
            self._breathing_update((pygame.time.get_ticks() % 3000) / 3000)
    
    def _breathing_update(self, progress):
        # 轻微的呼吸动画
        breath = math.sin(progress * 2 * math.pi) * 2
        self.parts['body']['angle'] = breath * 0.5
        self.parts['head']['angle'] = breath * 0.3
        self.parts['left_arm']['angle'] = breath * 1
        self.parts['right_arm']['angle'] = breath * 1
        self.base_offset[1] = abs(breath) * 1  # 轻微上下移动
    
    def _reset_pose(self):
        # 重置所有部件到默认位置
        self.is_breathing = False  # 停止呼吸动画
        for part in self.parts.values():
            part['angle'] = 0
        self.base_offset = [0, 0]
        
        # 设置默认姿势 - 自然站立
        self.parts['left_arm']['angle'] = 0
        self.parts['right_arm']['angle'] = 0
        self.parts['left_leg']['angle'] = 0
        self.parts['right_leg']['angle'] = 0

    def play_animation(self, action_id):
        self.current_animation = action_id
        self.animation_time = 0
        self.animation_frame = 0

    def set_pose(self, pose_data):
        for part_name, settings in pose_data.items():
            if part_name in self.parts:
                for key, value in settings.items():
                    self.parts[part_name][key] = value

if __name__ == "__main__":
    editor = SceneEditor()
    editor.run() 