import sys
import os
import re
import json
import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

from PyQt6.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, QTimer, QUrl
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QGraphicsDropShadowEffect,
                             QListWidget, QListWidgetItem, QSplitter, QLabel, QMessageBox,
                             QTextBrowser)
from PyQt6.QtGui import QColor, QTextCursor

from config_manager import ConfigManager
from conversation_manager import ConversationManager
from models import Message, Role, Conversation
from lm_client import LMStudioStreamWorker

DARK_STYLESHEET = """
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QSplitter::handle {
    background-color: #313244;
    width: 2px;
}
QListWidget {
    background-color: #11111b;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 5px;
}
QListWidget::item {
    padding: 10px;
    border-radius: 6px;
    margin-bottom: 2px;
}
QListWidget::item:hover {
    background-color: #181825;
}
QListWidget::item:selected {
    background-color: #313244;
    color: #89b4fa;
    font-weight: bold;
}
QPushButton {
    background-color: #313244;
    border: none;
    border-radius: 6px;
    padding: 8px 12px;
    color: #cdd6f4;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #45475a;
}
QPushButton:pressed {
    background-color: #585b70;
}
QPushButton#DeleteBtn {
    background-color: #f38ba8;
    color: #11111b;
}
QPushButton#DeleteBtn:hover {
    background-color: #eba0b2;
}
QLineEdit {
    background-color: #11111b;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 8px;
    color: #cdd6f4;
}
QLineEdit:focus {
    border: 1px solid #89b4fa;
}
QLabel#StatusLabel {
    color: #fab387;
    font-size: 12px;
    font-weight: bold;
    padding: 2px 5px;
}
QScrollBar:vertical {
    border: none;
    background: #11111b;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #45475a;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QTextBrowser {
    background-color: #11111b;
    border: none;
    margin: 0px;
    padding: 10px;
}
"""

class AIAgentUI(QWidget):
    def __init__(self, conversation_manager, config_manager, router=None, system_prompt=None):
        super().__init__()
        self.conv_manager = conversation_manager
        self.config = config_manager
        self.router = router
        self.system_prompt = system_prompt
        self.screen_geo = QApplication.primaryScreen().geometry()
        self.is_expanded = False
        self.current_worker = None
        self.debug_mode = True
        self.current_conversation_id = None
        self.chat_loaded = True  # textbrowser не требует асинхронной загрузки
        self.pending_tool_processing = False
        self.pending_tool_call = None

        self.code_blocks = {}       # id -> (language, code)
        self.thought_states = {}    # id -> expanded (True/False)
        self.thought_counter = 0
        self.code_counter = 0

        self.init_ui()
        self.load_conversations()
        if not self.conv_manager.conversations:
            self.new_conversation()

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("MainWindow")
        self.setStyleSheet(DARK_STYLESHEET)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Левая панель
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)

        btn_layout = QHBoxLayout()
        new_dialog_btn = QPushButton("➕ Новый")
        new_dialog_btn.clicked.connect(self.new_conversation)
        delete_dialog_btn = QPushButton("🗑️")
        delete_dialog_btn.setObjectName("DeleteBtn")
        delete_dialog_btn.clicked.connect(self.delete_current_conversation)
        btn_layout.addWidget(new_dialog_btn)
        btn_layout.addWidget(delete_dialog_btn)
        left_layout.addLayout(btn_layout)

        self.dialog_list = QListWidget()
        self.dialog_list.itemClicked.connect(self.on_dialog_selected)
        left_layout.addWidget(self.dialog_list)

        # Правая панель
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)

        top_bar = QHBoxLayout()
        self.title_label = QLabel("AI Agent")
        self.title_label.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 14px;")
        self.expand_btn = QPushButton("⛶")
        self.expand_btn.setFixedSize(30, 30)
        self.expand_btn.clicked.connect(self.toggle_size)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.hide_window)
        top_bar.addWidget(self.title_label)
        top_bar.addStretch()
        top_bar.addWidget(self.expand_btn)
        top_bar.addWidget(close_btn)
        right_layout.addLayout(top_bar)

        self.status_label = QLabel("Готов к работе")
        self.status_label.setObjectName("StatusLabel")
        right_layout.addWidget(self.status_label)

        # QTextBrowser вместо QWebEngineView
        self.chat_area = QTextBrowser()
        self.chat_area.setOpenLinks(False)  # перехватываем клики сами
        self.chat_area.anchorClicked.connect(self.handle_chat_links)
        self.chat_area.setStyleSheet("""
            QTextBrowser {
                background-color: #11111b;
                border: none;
                padding: 8px;
            }
        """)
        right_layout.addWidget(self.chat_area, 1)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Напишите запрос...")
        self.input_field.returnPressed.connect(self.send_message)
        send_btn = QPushButton("Отправить")
        send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(send_btn)
        right_layout.addLayout(input_layout)

        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        left_panel.setMinimumWidth(140)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(main_splitter)

        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.setDuration(self.config.get("ui.animation_duration", 300))

    # --- Работа с markdown и рендерингом ---

    def render_markdown_to_html(self, content: str, is_thought=False, thought_id=None) -> str:
        """Преобразует markdown в HTML с поддержкой подсветки кода и сворачиваемых блоков мыслей."""
        if is_thought and thought_id:
            expanded = self.thought_states.get(thought_id, False)
            toggle_link = f'<a href="toggle:{thought_id}" class="thought-toggle">{ "🧠 Свернуть размышления" if expanded else "🧠 Размышления агента (развернуть...)" }</a>'
            if expanded:
                body_html = markdown.markdown(content, extensions=['fenced_code', 'codehilite'])
                return f'<div class="thought-block">{toggle_link}<div class="thought-body">{body_html}</div></div>'
            else:
                return f'<div class="thought-block collapsed">{toggle_link}</div>'
        else:
            # Обычный текст с подсветкой кода и кнопками копирования
            return self.process_code_blocks(markdown.markdown(content, extensions=['fenced_code', 'codehilite']))

    def process_code_blocks(self, html: str) -> str:
        """Находит div'ы с классами codehilite и добавляет кнопку копирования с символом ❏."""
        def replacer(match):
            code_content = match.group(1)
            self.code_counter += 1
            block_id = f"code_{self.code_counter}"
            clean_code = re.sub(r'<.*?>', '', code_content)
            self.code_blocks[block_id] = clean_code
            # Кнопка с символом ❏
            button = f'<div class="code-header"><a href="copy:{block_id}" class="copy-btn">❏ Копировать</a></div>'
            return button + match.group(0)

        pattern = r'(<div class="codehilite">.*?</div>)'
        return re.sub(pattern, replacer, html, flags=re.DOTALL)

    def build_full_chat_html(self, messages: list) -> str:
        """Собирает весь чат в один HTML-документ с учётом состояний сворачивания и роли THINKING."""
        # Сбрасываем счётчики ID, чтобы ID оставались стабильными при обновлении UI
        self.code_blocks.clear()
        self.code_counter = 0
        self.thought_counter = 0

        chat_parts = []
        for idx, msg in enumerate(messages):
            if msg.role == Role.USER:
                chat_parts.append(f'<div class="message user-message"><div class="name">Вы:</div><div class="content">{self.escape_html(msg.content)}</div></div>')

            elif msg.role == Role.ASSISTANT:
                blocks = self.parse_thinking_and_text(msg.content)
                assistant_html = '<div class="message assistant-message"><div class="name">🤖 Агент:</div><div class="content">'
                for b_type, b_content in blocks:
                    if b_type == 'text':
                        assistant_html += self.render_markdown_to_html(b_content, is_thought=False)
                    elif b_type == 'thinking':
                        self.thought_counter += 1
                        thought_id = f"thought_{self.thought_counter}"
                        if thought_id not in self.thought_states:
                            self.thought_states[thought_id] = False
                        assistant_html += self.render_markdown_to_html(b_content, is_thought=True, thought_id=thought_id)

                # Кнопка копирования всего ответа (очищаем от тегов размышлений)
                clean_text_to_copy = re.sub(r'<thinking>.*?</thinking>', '', msg.content, flags=re.DOTALL).strip()
                msg_copy_id = f"msg_{idx}"
                self.code_blocks[msg_copy_id] = clean_text_to_copy
                assistant_html += f'<div class="msg-footer"><a href="copy:{msg_copy_id}" class="copy-btn">❏ Копировать ответ</a></div>'
                assistant_html += '</div></div>'
                chat_parts.append(assistant_html)

            elif msg.role == Role.THINKING:
                # Отдельные блоки размышлений (если LMStudioStreamWorker их создаёт)
                self.thought_counter += 1
                thought_id = f"thought_{self.thought_counter}"
                if thought_id not in self.thought_states:
                    self.thought_states[thought_id] = False
                thinking_html = '<div class="message assistant-message"><div class="name">🤖 Агент (размышление):</div><div class="content">'
                thinking_html += self.render_markdown_to_html(msg.content, is_thought=True, thought_id=thought_id)
                thinking_html += '</div></div>'
                chat_parts.append(thinking_html)

            elif msg.role == Role.TOOL:
                chat_parts.append(f'<div class="tool-result">⚙️ Результат вызова инструмента:<br>{self.escape_html(msg.content)}</div>')

        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    background-color: #11111b;
                    color: #cdd6f4;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-size: 13px;
                    padding: 15px;
                    margin: 0;
                }}
                .message {{
                    margin-bottom: 20px;
                    border-bottom: 1px solid #313244;
                    padding-bottom: 10px;
                }}
                .user-message .name {{ color: #89b4fa; font-weight: bold; }}
                .assistant-message .name {{ color: #a6e3a1; font-weight: bold; }}
                .content {{
                    margin-top: 6px;
                    line-height: 1.5;
                }}
                .thought-block {{
                    background-color: #181825;
                    border-left: 4px solid #94e2d5;
                    border-radius: 8px;
                    margin: 12px 0;
                    overflow: hidden;
                }}
                .thought-toggle {{
                    display: inline-block;
                    background-color: #1e1e2e;
                    padding: 8px 12px;
                    cursor: pointer;
                    text-decoration: none;
                    color: #94e2d5;
                    font-weight: bold;
                    border-bottom: 1px solid #313244;
                    width: 100%;
                }}
                .thought-body {{
                    padding: 12px;
                    color: #bac2de;
                    font-style: italic;
                    line-height: 1.5;
                }}
                .code-header, .msg-footer {{
                    margin-top: 10px;
                    text-align: right;
                }}
                .copy-btn {{
                    display: inline-block;
                    background-color: #313244;
                    color: #89b4fa;
                    text-decoration: none;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                }}
                .copy-btn:hover {{
                    background-color: #45475a;
                }}
                .tool-result {{
                    background-color: #2a2a3a;
                    padding: 8px;
                    border-radius: 6px;
                    color: #cdd6f4;
                    margin: 10px 0;
                    font-family: monospace;
                }}
                pre {{
                    background-color: #1e1e2e;
                    padding: 10px;
                    border-radius: 6px;
                    overflow-x: auto;
                }}
                code {{
                    font-family: monospace;
                    background-color: #1e1e2e;
                    padding: 2px 4px;
                    border-radius: 3px;
                }}
                .codehilite {{
                    background-color: #1e1e2e;
                    border-radius: 6px;
                    margin: 5px 0;
                }}
            </style>
        </head>
        <body>
            {''.join(chat_parts)}
        </body>
        </html>
        """
        return full_html

    def escape_html(self, text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def parse_thinking_and_text(self, raw_text: str):
        """Разбивает текст на части: ('text', ...) и ('thinking', ...)"""
        blocks = []
        current_pos = 0
        text_len = len(raw_text)
        while current_pos < text_len:
            start_tag = raw_text.find('<thinking>', current_pos)
            if start_tag == -1:
                plain_part = raw_text[current_pos:]
                if plain_part.strip():
                    blocks.append(('text', plain_part))
                break
            if start_tag > current_pos:
                before = raw_text[current_pos:start_tag]
                if before.strip():
                    blocks.append(('text', before))
            end_tag = raw_text.find('</thinking>', start_tag + 10)
            if end_tag == -1:
                thinking_part = raw_text[start_tag + 10:]
                if thinking_part.strip():
                    blocks.append(('thinking', thinking_part))
                break
            else:
                thinking_part = raw_text[start_tag + 10:end_tag]
                if thinking_part.strip():
                    blocks.append(('thinking', thinking_part))
                current_pos = end_tag + 11
        return blocks

    def refresh_chat_display(self):
        """Перерисовывает весь чат на основе текущей конверсии."""
        conv = self.conv_manager.current_conversation
        if conv:
            html = self.build_full_chat_html(conv.messages)
            self.chat_area.setHtml(html)
            # Прокручиваем вниз
            self.chat_area.moveCursor(QTextCursor.MoveOperation.End)

    def handle_chat_links(self, url: QUrl):
        """Обрабатывает клики по специальным ссылкам вида copy:... или toggle:..."""
        scheme = url.scheme()
        path = url.path()
        if scheme == "copy":
            code = self.code_blocks.get(path, "")
            if code:
                QApplication.clipboard().setText(code)
                self.status_label.setText(f"Скопировано: {path}")
                QTimer.singleShot(2000, lambda: self.status_label.setText("Готов к работе"))
        elif scheme == "toggle":
            if path in self.thought_states:
                self.thought_states[path] = not self.thought_states[path]
                self.refresh_chat_display()

    # --- Работа с конверсиями и стримингом ---

    def display_conversation(self, conv: Conversation):
        self.current_conversation_id = conv.id
        self.thought_states.clear()
        self.thought_counter = 0
        self.refresh_chat_display()

    def update_status(self, text: str):
        self.status_label.setText(text)

    def on_thinking_part(self, text):
        conv = self.conv_manager.current_conversation
        if not conv:
            return
        if conv.messages and conv.messages[-1].role == Role.ASSISTANT:
            if "<thinking>" not in conv.messages[-1].content:
                conv.messages[-1].content += "<thinking>" + text
            else:
                if conv.messages[-1].content.endswith("</thinking>"):
                    conv.messages[-1].content += "<thinking>" + text
                else:
                    conv.messages[-1].content += text
        elif conv.messages and conv.messages[-1].role == Role.THINKING:
            conv.messages[-1].content += text
        else:
            conv.add_message(Message(Role.THINKING, text))
        self.refresh_chat_display()

    def on_response_part(self, text):
        conv = self.conv_manager.current_conversation
        if not conv:
            return
        if conv.messages and conv.messages[-1].role == Role.THINKING:
            raw_thinking = conv.messages[-1].content
            conv.messages.pop()
            conv.add_message(Message(Role.ASSISTANT, f"<thinking>{raw_thinking}</thinking>{text}"))
        elif conv.messages and conv.messages[-1].role == Role.ASSISTANT:
            content = conv.messages[-1].content
            if "<thinking>" in content and not content.endswith("</thinking>") and "</thinking>" not in content[content.find("<thinking>"):]:
                conv.messages[-1].content += "</thinking>"
            conv.messages[-1].content += text
        else:
            conv.add_message(Message(Role.ASSISTANT, text))
        self.refresh_chat_display()

    def on_stream_finished(self):
        if self.pending_tool_processing:
            self.pending_tool_processing = False
            return
        if self.current_worker and hasattr(self.current_worker, 'pending_tool_call'):
            pending_tool_call = self.current_worker.pending_tool_call
        self.cleanup_worker()
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
        self.current_worker = None
        self.update_status("Готов к работе")

        conv = self.conv_manager.current_conversation
        if not conv:
            return

        if conv.messages and conv.messages[-1].role == Role.ASSISTANT:
            content = conv.messages[-1].content
            if content.count("<thinking>") > content.count("</thinking>"):
                conv.messages[-1].content += "</thinking>"
                self.refresh_chat_display()

        if len(conv.messages) >= 2 and (not conv.title or conv.title.startswith("Новый диалог") or conv.title.startswith("привет")):
            first_user = conv.messages[0].content
            conv.title = first_user[:20] + "..." if len(first_user) > 20 else first_user
            self.title_label.setText(conv.title)
            self.update_conversation_list_title(conv.id, conv.title)

        self.conv_manager.save_conversation(conv)

        if self.pending_tool_call:
            tool_name, tool_args = self.pending_tool_call
            if self.debug_mode:
                print(f"[DEBUG] Вызов инструмента: {tool_name} с аргументами {tool_args}")
            try:
                result = self.router.execute(tool_name, tool_args)
                tool_result_str = json.dumps(result, ensure_ascii=False, indent=2)
                if self.debug_mode:
                    print(f"[DEBUG] Результат: {tool_result_str}")
            except Exception as e:
                tool_result_str = f"Ошибка при выполнении: {e}"
                print(f"[ERROR] {tool_result_str}")

            if conv.messages and conv.messages[-1].role == Role.ASSISTANT:
                import re
                clean = re.sub(r'\[TOOL_CALL\]\s*\{.*?\}', '', conv.messages[-1].content, flags=re.DOTALL)
                conv.messages[-1].content = clean.strip()
                self.refresh_chat_display()

            tool_msg = Message(Role.TOOL, tool_result_str)
            conv.add_message(tool_msg)
            self.refresh_chat_display()
            self.conv_manager.save_conversation(conv)

            # Продолжаем диалог после вызова инструмента
            self.current_worker = LMStudioStreamWorker(
                conversation=conv,
                config_manager=self.config,
                system_prompt=self.system_prompt,
                router=self.router
            )
            self.current_worker.tool_calls_detected.connect(self.on_tool_calls_detected)
            self.current_worker.status_changed.connect(self.update_status)
            self.current_worker.thinking_part.connect(self.on_thinking_part)
            self.current_worker.response_part.connect(self.on_response_part)
            self.current_worker.finished.connect(self.on_stream_finished)
            self.current_worker.error_occurred.connect(self.on_stream_error)
            self.current_worker.start()
        else:
            self.update_conversation_list_title(conv.id, conv.title)

    def on_stream_error(self, error_msg):
        self.cleanup_worker()
        self.input_field.setEnabled(True)
        self.update_status("Ошибка API")
        conv = self.conv_manager.current_conversation
        if conv:
            conv.add_message(Message(Role.ASSISTANT, f"❌ **Ошибка:** {error_msg}"))
            self.refresh_chat_display()

    # Переподключаем новый сигнал:
    # worker.tool_calls_detected.connect(self.on_tool_calls_detected)

    def on_tool_calls_detected(self, tool_calls, text_before):
        """
        Слот-контроллер: обрабатывает вызовы инструментов, выполняет их,
        записывает результаты в историю диалога и пинает модель на финальный ответ.
        """
        self.pending_tool_processing = True

        # --- ИСПРАВЛЕНИЕ ДВОЙНОГО ОТВЕТА ---
        # Стример во время работы уже добавлял чанки в последнее сообщение диалога.
        # Вместо создания НОВОГО сообщения, мы просто берем последнее сообщение ассистента 
        # и гарантируем, что его контент равен полному тексту из воркера.
        conv = self.conv_manager.current_conversation
        if not conv:
            return

        worker = self.sender()
        full_assistant_text = worker._full_response if worker else text_before

        if conv.messages and conv.messages[-1].role == Role.ASSISTANT:
            # Обновляем существующее сообщение, а не плодим дубликаты
            conv.messages[-1].content = full_assistant_text
        else:
            # На случай, если почему-то сообщения не было (крайне маловероятно)
            assistant_msg = Message(role=Role.ASSISTANT, content=full_assistant_text)
            self.conv_manager.add_message_to_current(assistant_msg)

        # Перед тем как запускать новый цикл генерации, принудительно гасим текущий воркер,
        # чтобы очистить поток и не ловить блокировки `if self.current_worker`
        self.cleanup_worker()

        # --- ВЫПОЛНЕНИЕ ТУЛОВ ---
        response_blocks = []
        for name, args, raw_chunk, error in tool_calls:
            if error:
                result_str = f"{{\n  \"error\": \"{error}\"\n}}"
            elif not name:
                result_str = "{\n  \"error\": \"Не удалось распознать имя инструмента\"\n}"
            else:
                try:
                    # Выполняем логику инструмента через роутер
                    result = self.router.execute(name, args)
                    result_str = json.dumps(result, ensure_ascii=False, indent=2)
                except Exception as e:
                    result_str = f"{{\n  \"error\": \"Исключение при выполнении: {str(e)}\"\n}}"

            # Нативный формат ответа среды для модели (XML)
            block = f"<tool_responses>\n<name>{name}</name>\n<content>{result_str}</content>\n</tool_responses>"
            response_blocks.append(block)

        tool_content = "\n".join(response_blocks)

        # Сохраняем результаты выполнения тулов в историю переписки
        tool_msg = Message(role=Role.TOOL, content=tool_content)
        self.conv_manager.add_message_to_current(tool_msg)

        # Обновляем интерфейс, чтобы пользователь сразу увидел красивую плашку вызова тула
        self.refresh_chat_display()
        self.update_status("⚙️ Инструменты выполнены. Запуск финального ответа...")

        # --- ИСПРАВЛЕНИЕ ПОВТОРНОГО ПИНКА ---
        # Запускаем повторную генерацию (модель увидит историю со своим вызовом и ответом тула)
        self.start_agent_generation()

    def start_agent_generation(self):
        """
        Внутренний метод для запуска генерации на основе текущего состояния истории.
        Используется как при отправке нового сообщения пользователем, так и при пинке после тулов.
        """
        conv = self.conv_manager.current_conversation
        if not conv:
            return
        if self.current_worker and self.current_worker.isRunning():
            return

        # Блокируем ввод на время генерации
        self.input_field.setEnabled(False)
        
        # Создаем новый поток воркера
        self.current_worker = LMStudioStreamWorker(
            conversation=conv,
            config_manager=self.config,
            system_prompt=self.system_prompt,
            router=self.router
        )
        
        # Переподключаем все сигналы
        self.current_worker.tool_calls_detected.connect(self.on_tool_calls_detected)
        self.current_worker.status_changed.connect(self.update_status)
        self.current_worker.thinking_part.connect(self.on_thinking_part)
        self.current_worker.response_part.connect(self.on_response_part)
        self.current_worker.finished.connect(self.on_stream_finished)
        self.current_worker.error_occurred.connect(self.on_stream_error)
        
        # Поехали!
        self.current_worker.start()
    
    def cleanup_worker(self):
        if self.current_worker is not None:
            self.current_worker.stop()
            self.current_worker.quit()
            self.current_worker.wait()
            self.current_worker.deleteLater()
            self.current_worker = None

    # --- Работа со списком диалогов ---

    def load_conversations(self):
        current_id = None
        if self.dialog_list.currentItem():
            current_id = self.dialog_list.currentItem().data(Qt.ItemDataRole.UserRole)
        convs = self.conv_manager.load_all_conversations()
        self.dialog_list.clear()
        target_item = None
        for conv in convs:
            title = conv.title if conv.title else "Пустой диалог"
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, conv.id)
            self.dialog_list.addItem(item)
            if current_id and conv.id == current_id:
                target_item = item
        if target_item:
            self.dialog_list.setCurrentItem(target_item)
        elif convs:
            self.dialog_list.setCurrentRow(0)
            self.on_dialog_selected(self.dialog_list.item(0))

    def on_dialog_selected(self, item):
        self.cleanup_worker()
        conv_id = item.data(Qt.ItemDataRole.UserRole)
        conv = next((c for c in self.conv_manager.conversations if c.id == conv_id), None)
        if conv:
            self.conv_manager.set_current_conversation(conv)
            self.title_label.setText(conv.title if conv.title else "Диалог")
            self.display_conversation(conv)

    def new_conversation(self):
        self.cleanup_worker()
        conv = self.conv_manager.new_conversation()
        self.load_conversations()
        for i in range(self.dialog_list.count()):
            item = self.dialog_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == conv.id:
                self.dialog_list.setCurrentItem(item)
                break
        self.display_conversation(conv)

    def delete_current_conversation(self):
        conv = self.conv_manager.current_conversation
        if not conv:
            return
        reply = QMessageBox.question(self, 'Удаление чата', f"Удалить чат '{conv.title}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if hasattr(self.conv_manager, 'delete_conversation'):
                self.conv_manager.delete_conversation(conv.id)
            else:
                if conv in self.conv_manager.conversations:
                    self.conv_manager.conversations.remove(conv)
                conv_dir = self.config.get("conversations_dir", "conversations")
                target_path = os.path.join(conv_dir, f"{conv.id}.json")
                if os.path.exists(target_path):
                    try:
                        os.remove(target_path)
                    except:
                        pass
            self.load_conversations()
            if self.dialog_list.count() == 0:
                self.new_conversation()

    def send_message(self):
        text = self.input_field.text().strip()
        if not text or self.current_worker:
            return
            
        user_msg = Message(Role.USER, text)
        self.conv_manager.add_message_to_current(user_msg)
        self.refresh_chat_display()
        self.input_field.clear()
        
        # Просто вызываем централизованный запуск генерации
        self.start_agent_generation()

    def update_conversation_list_title(self, conv_id, new_title):
        for i in range(self.dialog_list.count()):
            item = self.dialog_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == conv_id:
                item.setText(new_title)
                break

    # --- Анимация и геометрия ---

    def get_side_panel_rect(self) -> QRect:
        default_width = self.config.get("ui.default_width", 400)
        margin = self.config.get("ui.default_margin", 20)
        height = self.screen_geo.height() - 100
        x = self.screen_geo.width() - default_width - margin
        y = (self.screen_geo.height() - height) // 2
        return QRect(x, y, default_width, height)

    def get_centered_rect(self) -> QRect:
        width = int(self.screen_geo.width() * 0.6)
        height = int(self.screen_geo.height() * 0.7)
        x = (self.screen_geo.width() - width) // 2
        y = (self.screen_geo.height() - height) // 2
        return QRect(x, y, width, height)

    def show_animated(self):
        if self.isVisible():
            return
        start_rect = self.get_side_panel_rect()
        start_rect.setX(self.screen_geo.width())
        self.setGeometry(start_rect)
        self.show()
        self.raise_()
        self.activateWindow()
        self.animation.setStartValue(start_rect)
        self.animation.setEndValue(self.get_side_panel_rect())
        self.animation.start()
        self.is_expanded = False
        self.expand_btn.setText("⛶")

    def hide_window(self):
        self.hide()

    def toggle_size(self):
        self.animation.stop()
        self.animation.setStartValue(self.geometry())
        if self.is_expanded:
            self.animation.setEndValue(self.get_side_panel_rect())
            self.expand_btn.setText("⛶")
        else:
            self.animation.setEndValue(self.get_centered_rect())
            self.expand_btn.setText("🗗")
        self.is_expanded = not self.is_expanded
        self.animation.start()