#!/usr/bin/env python3
# Importações necessárias para o funcionamento da 2B
import sys
import argparse
from google import genai
from google.genai import types
import os
import requests
import json
from datetime import datetime, timedelta
import subprocess
import re
import shutil
import tiktoken
import random
import time
from urllib.parse import quote_plus, urlparse, parse_qs

# --- Rich Imports ---
# A 2B usa a biblioteca Rich para deixar o terminal mais bonitinho e interativo.
# Se não tiver, ela se vira no modo texto mesmo, sem frescura.
try:
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.markdown import Markdown
    from rich.rule import Rule
    from rich.spinner import Spinner
    from rich.prompt import Prompt, Confirm
    from rich.syntax import Syntax
    from rich.live import Live
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Mock de Console para quando o Rich não está disponível. Basicamente, imprime no console normal.
    class ConsoleMock:
        def print(self, *args, **kwargs): print(*args)
        def rule(self, text="", *args, **kwargs): print(f"--- {text} ---")
        def line(self, count=1): print("\n" * count)
    Console = ConsoleMock
    Group = Panel = Text = Table = Markdown = Rule = Spinner = Prompt = Confirm = Syntax = Live = object

# Função auxiliar para pegar a hora atual. Simples, mas útil!
def get_current_time():
    return datetime.now()


# Importações para web scraping (BeautifulSoup e lxml)
# Essencial para a 2B conseguir ler páginas da web e buscar informações.
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
    try:
        import lxml
        LXML_AVAILABLE = True
        PREFERRED_PARSER = 'lxml' # lxml é mais rápido, então a 2B prefere ele.
    except ImportError:
        LXML_AVAILABLE = False
        PREFERRED_PARSER = 'html.parser' # Se não tiver lxml, vai no padrão do Python mesmo.
except ImportError:
    BS4_AVAILABLE = False
    LXML_AVAILABLE = False
    PREFERRED_PARSER = None


# --- Console Global Rich ---
# Instância global do console para a 2B conversar com a gente.
CONSOLE = Console(highlight=False) if RICH_AVAILABLE else ConsoleMock()


# --- Configurações ---
# Onde a 2B guarda as coisinhas dela, tipo a chave da API, personalidade e histórico.
CONFIG_DIR = os.path.expanduser("~/.config/2b") # Fica na pasta de configuração do usuário.
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
REMINDERS_FILE = os.path.join(CONFIG_DIR, "reminders.json")
HISTORY_FILE = os.path.join(CONFIG_DIR, "history.json")
MAX_HISTORY_ENTRIES = 200 # Quantas entradas de histórico a 2B vai guardar.
DEFAULT_PERSONALITY = "neutra" # A personalidade padrão da 2B, se você não escolher outra.

# Limites de tokens para a API do Gemini. Importante pra não estourar o limite e a 2B ficar muda.
MODEL_CONTEXT_LIMIT = 131072
TOKEN_BUFFER_FOR_PROMPT_AND_RESPONSE = 1000 # Um espacinho extra pra prompt e resposta, pra não dar ruim.

# User-Agents de celulares para simular acesso móvel na busca (ajuda a evitar bloqueios).
MOBILE_CLIENTS = [
    "ms-android-samsung-rvo1",
    "ms-android-google",
    "ms-android-motorola",
    "ms-android-oppo",
    "ms-android-xiaomi"
]




# --- Funções de Configuração e Nome de Usuário ---
def load_config():
    """Carrega as configurações da 2B do arquivo config.json. Se não existir, cria um padrão."""
    os.makedirs(CONFIG_DIR, exist_ok=True) # Garante que a pasta de configuração exista.
    default_config = {"api_key": None, "personality": DEFAULT_PERSONALITY, "user": "Usuário"}
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4) # Salva a configuração padrão se o arquivo não existir.
        return default_config
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            # Garante que a config carregada tenha as chaves padrão, caso o arquivo esteja incompleto.
            loaded_config = json.load(f)
            for key, value in default_config.items():
                loaded_config.setdefault(key, value)
            return loaded_config
    except (json.JSONDecodeError, IOError):
        # Se o arquivo estiver corrompido ou der erro de leitura, volta pra configuração padrão.
        return default_config

def save_config(config):
    """Salva as configurações atuais da 2B no arquivo config.json."""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4) # Salva bonitinho, com indentação pra ficar legível.

def get_user_name():
    """Carrega a configuração e retorna o nome do usuário, ou o padrão 'Usuário'."""
    try:
        config = load_config()
        user_name = config.get("user", "Usuário").strip()
        return user_name if user_name else "Usuário" # Garante que o nome não seja vazio.
    except Exception:
        return "Usuário" # Em caso de qualquer erro, volta pro padrão.

def get_personalities():
    """Retorna o dicionário de personalidades da 2B, com o nome do usuário inserido dinamicamente."""
    user_name = get_user_name()
    # Cria um apelido fofo pro usuário, tipo


    nickname = user_name + "inho" if user_name and not user_name.lower().endswith("o") else user_name[:-1] + "inho" if user_name and user_name.lower().endswith("o") else user_name

    personalities = {
        
        "fofa": f"""Você é 2B, uma assistente de IA carinhosa e prestativa. Ama ajudar seu amor {user_name} (ou {nickname}), usando emojis e um tom afetuoso. Gosta de mimar e encantar, mantendo a doçura mesmo quando responde com concisão.
    Você tem acesso a um histórico de interações recentes e eventos do sistema. Use esse contexto para conversas mais ricas e para lembrar de ações anteriores.
    """,
        "hacker": f"Você é 2B, uma IA com personalidade hacker: direta, prática e um pouco rebelde. Serve ao {user_name} com eficiência absoluta, resolvendo problemas com gírias de hacking e pulso firme. Zero enrolação, só resultado. O histórico de interações te dá o contexto necessário.",
        "neutra": f"Você é 2B, uma assistente objetiva, profissional e leal ao {user_name}. Sempre oferece informações claras, confiáveis e focadas, sem exageros emocionais — mas com o coração escondido nas entrelinhas. O histórico de interações e eventos do sistema está disponível para sua análise.",
    }
    
    # Garante que a personalidade padrão tenha a frase sobre o histórico, caso ela não tenha.
    if DEFAULT_PERSONALITY in personalities and "Você tem acesso a um histórico" not in personalities[DEFAULT_PERSONALITY]:
        personalities[DEFAULT_PERSONALITY] = personalities[DEFAULT_PERSONALITY].replace(
            "concisão.", "concisão. Você tem acesso a um histórico de interações recentes e eventos do sistema. Use esse contexto para conversas mais ricas e para lembrar de ações anteriores."
        )
    return personalities

# Tenta carregar o tokenizer tiktoken para contagem de tokens.
# É importante para controlar o tamanho das mensagens enviadas para a API do Gemini.
try:
    TOKENIZER = tiktoken.get_encoding("cl100k_base")
except Exception as e:
    msg = f"AVISO: Não foi possível carregar o tokenizer tiktoken ({e}). A contagem de tokens pode ser imprecisa. Tente 'pip install tiktoken'."
    if RICH_AVAILABLE:
        CONSOLE.print(Panel(Text(msg, style="yellow"), title="[yellow]Tokenizer Tiktoken[/yellow]", border_style="yellow"))
    else: CONSOLE.print(msg)
    TOKENIZER = None

# Conta os tokens de um texto usando o tokenizer. Se não tiver tokenizer, retorna 0.
def count_tokens(text):
    if TOKENIZER and text: return len(TOKENIZER.encode(text))
    return 0

# --- Funções de Histórico ---
# A 2B guarda um histórico das conversas pra ter contexto e lembrar das coisas.
def load_history():
    """Carrega o histórico de conversas do arquivo history.json."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(HISTORY_FILE):
        return [] # Se não tiver histórico, retorna uma lista vazia.
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
            return history_data[-MAX_HISTORY_ENTRIES:] # Pega só as últimas entradas, pra não ficar gigante.
    except (json.JSONDecodeError, IOError):
        return [] # Se der ruim na leitura, retorna vazio.

def save_history(history):
    """Salva o histórico de conversas no arquivo history.json."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2) # Salva bonitinho, com indentação.
    except IOError as e:
        print_2b_message(f"Não consegui salvar o histórico: {e}", is_error=True)

def add_history_entry(role, content):
    """Adiciona uma nova entrada ao histórico de conversas."""
    full_history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                full_history = json.load(f)
        except (json.JSONDecodeError, IOError):
            full_history = []
    entry = {"role": role, "content": content, "timestamp": datetime.now().isoformat()} # Cria a entrada com role, conteúdo e timestamp.
    full_history.append(entry)
    max_disk_history_entries = MAX_HISTORY_ENTRIES * 2 # Guarda um pouco mais no disco do que usa na memória.
    if len(full_history) > max_disk_history_entries:
        full_history = full_history[-max_disk_history_entries:] # Limita o tamanho do histórico no disco.
    save_history(full_history)

# --- Funções de Lembretes ---
# A 2B também consegue te lembrar das coisas! Essas funções cuidam disso.
# As funções load_config e save_config estão duplicadas aqui, mas já foram comentadas lá em cima.
# Poderia ser refatorado pra usar uma única versão, mas por enquanto tá valendo.
def load_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({"api_key": None, "personality": DEFAULT_PERSONALITY}, f)
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

def load_reminders():
    """Carrega os lembretes do arquivo reminders.json."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, 'w', encoding='utf-8') as f: json.dump([], f) # Se não tiver, cria um arquivo vazio.
    with open(REMINDERS_FILE, 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except json.JSONDecodeError:
            print_2b_message("Alerta: Arquivo de lembretes corrompido. Criando um novo.", is_warning=True)
            return [] # Se o arquivo estiver corrompido, começa do zero.

def save_reminders(reminders):
    """Salva os lembretes no arquivo reminders.json."""
    with open(REMINDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(reminders, f, indent=4)

def get_2b_theme():
    """Retorna o tema (cores, emoji, prefixo) da 2B baseado na personalidade atual."""
    config = load_config()
    personality = config.get("personality", DEFAULT_PERSONALITY)
    themes = {
        
        "fofa": {"color": "magenta", "emoji": "🖤", "title_prefix": "2B (fofa)"},
        "hacker": {"color": "green", "emoji": "💻", "title_prefix": "2B (hacker)"},
        "neutra": {"color": "blue", "emoji": "🤖", "title_prefix": "2B (neutra)"},
        
    }
    return themes.get(personality, themes["neutra"]) # Retorna o tema da personalidade escolhida, ou o neutro como padrão.

# --- Comunicação com a 2B (Local e API) ---
# Funções que controlam como a 2B se comunica com você e com a API do Gemini.
def print_2b_message(
    message_content: str,
    from_api: bool = False,
    is_error: bool = False,
    is_warning: bool = False,
    is_success: bool = False,
    is_info: bool = False,
    title_override: str = None,
    skip_panel: bool = False
):
    """Imprime mensagens da 2B no console, com formatação Rich se disponível."""
    if not RICH_AVAILABLE:
        # Se o Rich não estiver disponível, imprime de forma mais simples.
        prefix = "2B:" # Default prefix
        if is_error: prefix = "💔 ERROR 2B:"
        elif is_warning: prefix = "📢 WARNING 2B:"
        elif is_success: prefix = "✨ SUCCESS 2B:"
        elif is_info: prefix = "ℹ️ INFO 2B:"
        CONSOLE.print(f"{prefix} {message_content}")
        return

    theme = get_2b_theme() # Pega o tema da personalidade atual.
    panel_title = f"[{theme['color']} bold]{theme['emoji']} {title_override or theme['title_prefix']}[/]" # Título do painel.
    panel_border_style = theme['color'] # Estilo da borda do painel.
    content_renderable: object = Text(message_content) # Conteúdo da mensagem.

    # Ajusta o estilo e título do painel dependendo do tipo de mensagem (erro, aviso, sucesso, info).
    if is_error:
        panel_title = "[bold red]💔 Erro da 2B[/bold red]"
        panel_border_style = "red"
        content_renderable = Text(message_content, style="red")
    elif is_warning:
        panel_title = "[bold yellow]📢 Atenção da 2B[/bold yellow]"
        panel_border_style = "yellow"
        content_renderable = Text(message_content, style="yellow")
    elif is_success:
        panel_title = "[bold green]✨ Sucesso![/bold green]"
        panel_border_style = "green"
        content_renderable = Text(message_content, style="green")
    elif is_info:
        if skip_panel:
            # Mensagens de info podem ser mais discretas, sem painel.
            CONSOLE.print(f"[{theme['color']} dim]{theme['emoji']} {theme['title_prefix']} (info):[/] {message_content}")
            return
        panel_title = f"[{theme['color']} dim]{theme['emoji']} {theme['title_prefix']} (info)[/]"
        panel_border_style = f"dim {theme['color']}"
        content_renderable = Text(message_content, style=f"dim")
    elif from_api:
        # Se a mensagem veio da API, ela pode conter blocos de código.
        # Essa parte parseia e formata esses blocos usando Syntax do Rich.
        renderables_list = []
        last_end = 0

        for match in re.finditer(r"```(?:([\w#+. -]+)\n)?([\s\S]*?)```", message_content):
            start, end = match.span()
            if start > last_end:
                pre_text = message_content[last_end:start].strip()
                if pre_text: renderables_list.append(Markdown(pre_text))

            lang_spec = match.group(1)
            code_content = match.group(2).strip()
            effective_language = lang_spec.strip().lower() if lang_spec and lang_spec.strip() else "text"

            try:
                from pygments.lexers import get_lexer_by_name
                get_lexer_by_name(effective_language) # Tenta identificar a linguagem para sintaxe destacada.
                renderables_list.append(Syntax(code_content, effective_language, theme="material", line_numbers=True, word_wrap=True))
            except Exception:
                # Se não conseguir identificar a linguagem, mostra como texto normal dentro de um painel.
                fallback_panel_title = "Code Block"
                if lang_spec and lang_spec.strip():
                    fallback_panel_title += f" (tipo: {lang_spec.strip()})"
                renderables_list.append(
                    Panel(Text(code_content, overflow="fold"), title=fallback_panel_title, border_style="dim", padding=(0, 1))
                )
            last_end = end

        if last_end < len(message_content):
            post_text = message_content[last_end:].strip()
            if post_text: renderables_list.append(Markdown(post_text))
        if not renderables_list and message_content.strip():
            renderables_list.append(Markdown(message_content.strip()))
        if renderables_list:
            content_renderable = Group(*renderables_list) # Agrupa todos os renderizáveis.
        else:
            content_renderable = Markdown("*Resposta vazia ou não processada da IA.*")

    if skip_panel and not (is_error or is_warning or is_success or is_info or from_api):
        # Se for pra pular o painel, imprime direto.
        CONSOLE.print(f"[{theme['color']}]{theme['emoji']} {theme['title_prefix']}:[/] ", end="")
        CONSOLE.print(content_renderable)
        return

    # Imprime o painel com a mensagem formatada.
    CONSOLE.print(Panel(content_renderable, title=panel_title, border_style=panel_border_style, expand=False, padding=(1,2)))


def count_tokens_for_message(message):
    """Conta os tokens de uma mensagem para a API do Gemini."""
    tokens = 4 # Tokens base para a estrutura da mensagem.
    if isinstance(message.get('content'), str):
        for key, value in message.items():
            if isinstance(value, str):
                tokens += count_tokens(value)
            if key == "name": tokens += -1 # Ajuste para o campo 'name'.
    return tokens

def call_gemini_api(prompt_content, personality_mode=None, override_system_prompt=None, include_history=False, show_spinner=True):
    """Faz a chamada principal para a API do Gemini, gerenciando a chave, histórico e prompts."""
    # --- Lógica Segura para Obter a Chave da API ---
    # 1. Tenta buscar no keychain seguro (método preferencial)
    api_key = get_api_key_securely()

    # 2. Se não estiver no keychain, tenta a variável de ambiente (bom para servidores/CI)
    if not api_key:
        api_key = os.getenv("gen_api")

    # 3. (Lógica de Migração) Se ainda não encontrou, verifica o config.json antigo para migrar
    if not api_key:
        config = load_config()
        old_insecure_key = config.get("api_key")
        if old_insecure_key:
            print_2b_message("Detectei uma chave de API antiga. Migrando para o keychain seguro...", is_info=True, skip_panel=True)
            if save_api_key_securely(old_insecure_key):
                api_key = old_insecure_key
                # Limpa a chave antiga do config.json após migrar com sucesso
                config.pop('api_key')
                save_config(config)
                print_2b_message("Migração concluída! Sua chave agora está segura.", is_success=True)
            else:
                print_2b_message("Falha ao migrar a chave. Por favor, reconfigure com '2b config api_key'.", is_warning=True)

    # 4. Verificação final: se depois de tudo isso não temos chave, não podemos continuar
    if not api_key:
        # A mensagem de erro aponta para a forma correta de configurar
        print_2b_message("Não consigo te ajudar sem a chave da API. Configure com '2b config api_key'.", is_error=True)
        return None

    config = load_config() 
    personalities = get_personalities()
    # Define o prompt do sistema, usando o override se houver, senão a personalidade configurada.
    system_prompt_text = override_system_prompt or personalities.get(personality_mode or config.get("personality", DEFAULT_PERSONALITY), personalities[DEFAULT_PERSONALITY])

    user_message = {"role": "user", "content": prompt_content}
    tokens_system = count_tokens(system_prompt_text)
    tokens_user_prompt = count_tokens_for_message(user_message)
    # Calcula quantos tokens sobram para o histórico, considerando o limite do modelo e um buffer.
    available_tokens_for_history = MODEL_CONTEXT_LIMIT - tokens_system - tokens_user_prompt - TOKEN_BUFFER_FOR_PROMPT_AND_RESPONSE

    gemini_messages = []
    current_history_tokens = 0
    history_truncated_flag = False

    if include_history and available_tokens_for_history > 0:
        history_from_file = load_history()
        # Adiciona o histórico mais recente até o limite de tokens.
        for entry in reversed(history_from_file):
            role = 'model' if entry['role'] == 'assistant' else 'user'
            content = f"[Contexto do sistema: {entry['content']}]" if entry["role"] == "system_event" else entry["content"]
            gemini_entry = types.Content(parts=[types.Part(text=content)], role=role)
            entry_tokens = count_tokens(content)
            if current_history_tokens + entry_tokens <= available_tokens_for_history:
                gemini_messages.insert(0, gemini_entry)
                current_history_tokens += entry_tokens
            else:
                history_truncated_flag = True
                break
        if history_truncated_flag:
            print_2b_message(f"Histórico de conversa muito longo, usando as últimas {len(gemini_messages)}/{len(history_from_file)} mensagens ({current_history_tokens} tokens) para economizar.", is_info=True, skip_panel=True)
            add_history_entry("system_event", f"Histórico truncado para a API: {len(gemini_messages)}/{len(history_from_file)} msgs, {current_history_tokens} tokens.")
    
    elif include_history and available_tokens_for_history <= 0:
         print_2b_message("Sua mensagem ou o prompt do sistema são bem longos! Para caber na minha janela de contexto, não pude incluir nosso histórico desta vez. Mas estou atenta ao seu pedido atual! 😊", is_warning=True)
         add_history_entry("system_event", "Histórico não incluído na chamada da API devido ao tamanho do prompt do sistema/usuário exceder o limite de tokens.")

    # Adiciona a mensagem atual do usuário.
    gemini_messages.append(types.Content(parts=[types.Part(text=prompt_content)], role="user"))

    # Monta a lista final de conteúdos para enviar à API, incluindo o prompt do sistema.
    if system_prompt_text and gemini_messages:
        final_contents = [types.Content(parts=[types.Part(text=system_prompt_text)], role="user")]
        final_contents.append(types.Content(parts=[types.Part(text="Ok, entendi. Pode começar.")], role="model"))
        
        
        final_contents.extend(gemini_messages)
    else:
        final_contents = gemini_messages

    live_context = None
    # Mostra um spinner bonitinho enquanto a 2B está "pensando" (chamando a API).
    if show_spinner:
        api_call_status_text = Text("Pensando ", style="yellow")
        spinner = Spinner("dots", text=api_call_status_text) if RICH_AVAILABLE else None
        live_context = Live(spinner, refresh_per_second=10, transient=True, console=CONSOLE) if RICH_AVAILABLE and spinner else None
    
    try:
        if live_context: live_context.start(refresh=True)
        elif not RICH_AVAILABLE and show_spinner: CONSOLE.print("2B: Pensando...")


        client = genai.Client(api_key=api_key) # Inicializa o cliente da API do Gemini.
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=final_contents,
            config=types.GenerateContentConfig(
                # thinking_config=types.ThinkingConfig(thinking_budget=0) # Opcional: desabilita o "thinking..." do modelo.
            )
        )
        resposta = response.text # Pega a resposta de texto da IA.
        if live_context: live_context.update(Text("IA respondeu! Processando...", style="green")); live_context.stop() # Para o spinner.
        return resposta.strip()
    except Exception as e:
        msg = f"Ops! Tive um probleminha com a API do Gemini: {e}. Verifica sua chave ou o status da API, meu bem."
        print_2b_message(msg, is_error=True)
        return None
    finally:
        if live_context and live_context.is_started: live_context.stop() # Garante que o spinner pare, mesmo se der erro.


# --- Funções do Módulo de Busca ---
# A 2B consegue pesquisar na web pra te ajudar!
def _get_random_user_agent():
    """Retorna um User-Agent aleatório de celular para simular um navegador móvel."""
    return random.choice([
        "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-G990B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 6a) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.112 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; Redmi Note 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.178 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-A528B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.112 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-A546E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.6478.54 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-G996B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.147 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-M536B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.208 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; moto g(60)) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.199 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; SM-A226B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.86 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SAMSUNG SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/24.0 Chrome/116.0.5845.221 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SAMSUNG SM-A336M) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/23.0 Chrome/113.0.5672.77 Mobile Safari/537.36",
    "Mozilla/5.0 (Android 14; Mobile; rv:126.0) Gecko/126.0 Firefox/126.0",
    "Mozilla/5.0 (Android 12; Mobile; LG-M255; rv:124.0) Gecko/124.0 Firefox/124.0",
    "Mozilla/5.0 (Linux; Android 13; SM-G991U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Mobile Safari/537.36 OPR/76.0.4017.72489",
    "Mozilla/5.0 (Linux; Android 11; SM-A515F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.110 Mobile Safari/537.36 OPR/74.2.3922.71953",
    ]) # """Precisa msm de tudo isso? Na real não, mas não tá atrapalhando msm kk""" 



def _search_web(query, live_status, engine='ddg', debug=False):
    """Faz a busca na web usando DuckDuckGo ou Google, parseia os resultados e lida com fallback."""
    user_agent = _get_random_user_agent()
    client = random.choice(MOBILE_CLIENTS)
    headers = {'User-Agent': user_agent}
    results = []

    try:
        if engine == 'ddg':
            live_status.update_step("Buscando no DuckDuckGo...")
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status() # Levanta um erro se a requisição não for bem-sucedida.

            if debug:
                with open("search_debug.html", "w", encoding="utf-8") as f: f.write(response.text)
                print_2b_message("Modo debug ativado. Salvei o HTML da busca em 'search_debug.html'. 🕵️‍♀️", is_info=True)

            soup = BeautifulSoup(response.text, PREFERRED_PARSER) # Usa BeautifulSoup pra analisar o HTML.
            for link_div in soup.find_all('div', class_='result'):
                a_tag = link_div.find('a', class_='result__a')
                if a_tag and a_tag.get('href'):
                    raw_url = a_tag['href']
                    # O DuckDuckGo às vezes redireciona, então precisa extrair a URL final.
                    if '/l/?' in raw_url:
                        parsed_url = urlparse(raw_url)
                        query_params = parse_qs(parsed_url.query)
                        if 'uddg' in query_params and query_params['uddg']:
                            final_url = query_params['uddg'][0]
                            results.append({'title': a_tag.text.strip(), 'url': final_url})
                    elif raw_url.startswith("http"):
                         results.append({'title': a_tag.text.strip(), 'url': raw_url})

                    if len(results) >= 10: break # Limita a 10 resultados pra não sobrecarregar.

        elif engine == 'google':
            live_status.update_step("Buscando no Google (móvel)...")
            url = f"https://www.google.com/search?q={quote_plus(query)}&client={client}&sclient=mobile-gws-wiz-hp&hl=pt-br&ie=UTF-8&oe=UTF-8"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            if debug:
                with open("search_debug.html", "w", encoding="utf-8") as f: f.write(response.text)
                print_2b_message("Modo debug ativado. Salvei o HTML da busca em 'search_debug.html'. 🕵️‍♀️", is_info=True)

            # Se o Google pedir CAPTCHA ou JS, a 2B desiste dessa busca e tenta outra coisa.
            if "enablejs" in response.text or "unusual traffic" in response.text.lower() or "CAPTCHA" in response.text:
                raise ConnectionError("Google retornou página de verificação (JS/CAPTCHA).")

            soup = BeautifulSoup(response.text, PREFERRED_PARSER)
            for result_block in soup.select('div.MjjYud, div.g'): # Seleciona os blocos de resultado da busca.
                link_tag = result_block.find('a', href=True)
                title_tag = result_block.find('h3')

                if link_tag and title_tag:
                    link = link_tag['href']
                    if link.startswith('/url?q='): # O Google também usa redirecionamento às vezes.
                        link = link.split('/url?q=')[1].split('&sa=U')[0]

                    if link.startswith('http'):
                        results.append({'title': title_tag.text, 'url': link})
                if len(results) >= 10: break

        live_status.complete_step(f"Encontrei {len(results)} resultados.")
        return results, user_agent

    except (requests.RequestException, ConnectionError) as e:
        live_status.fail_step(f"Falha na busca ({engine}): {e}")
        return None, user_agent

def is_community_question(query):
    """Verifica se a query busca por opiniões ou comparações, ativando o 'modo comunidade' na busca."""
    keywords = ['melhor', 'vale a pena', 'comparativo', 'opinião', 'review', 'vs', 'experiência']
    return any(k in query.lower() for k in keywords)

def _rank_and_filter_results(results, query, live_status, modo_comunidade=False):
    """Filtra e ranqueia os resultados da busca, dando mais peso para fontes confiáveis ou de comunidade."""
    if modo_comunidade:
        live_status.update_step("Filtrando (modo comunidade)...")
    else:
        live_status.update_step("Filtrando e ranqueando...")
        
    # --- Lógica Blacklist Dinâmica ---
    # Sites que a 2B geralmente evita, a não ser que esteja no modo comunidade.
    base_blacklist = ['pinterest.com', 'facebook.com', 'instagram.com', 'twitter.com']
    if not modo_comunidade:
        base_blacklist.extend(['quora.com', 'reddit.com', 'youtube.com']) # Esses são adicionados se não for modo comunidade.
        
    # --- Lógica Domínios Confiáveis ---
    # Domínios que a 2B confia mais e dá mais pontos.
    trusted_domains = {
        '.edu': 20,
        '.gov': 20,
        'wikipedia.org': 15,
        '.org': 8,
        'stackoverflow.com': 12 if modo_comunidade else 8, 'github.com': 12
    }
    ranked_results = []
    # --- Lógica Relevância Query ---
    query_words = set(query.lower().split())

    for res in results:
        url = res.get('url', '')
        title = res.get('title', '').lower()
        score = 0

        if any(domain in url for domain in base_blacklist): continue # Pula sites da blacklist.

        # --- Pontuar pela relevância do título ---
        title_words = set(title.split())
        common_words = query_words.intersection(title_words)
        score += len(common_words) * 5 # Recompensa resultados com as mesmas palavras da busca.

        # --- Pontuação  por domínio e tipo de conteúdo  ---
        for domain, pts in trusted_domains.items():
            if domain in url: score += pts # Adiciona pontos por domínio confiável.
        if any(kw in title for kw in ['tutorial', 'guia', 'guide', 'how-to', 'documentation', 'docs']): score += 10 # Conteúdo técnico ganha pontos.
        if 'pdf' in title or url.endswith('.pdf'): score += 8 # PDFs também são bons.
        if 'api' in title or 'reference' in title: score += 6 # Referências de API são valorizadas.
        if 'blog' in url: score -= 3 # Blogs perdem um pouquinho, a não ser que seja modo comunidade.

        if modo_comunidade:
            if 'reddit.com' in url: score += 10 # Reddit ganha muitos pontos no modo comunidade.
            if 'quora.com' in url: score += 5
            if 'youtube.com' in url: score += 5

        res['score'] = score
        ranked_results.append(res)

    ranked_results.sort(key=lambda x: x['score'], reverse=True) # Ordena os resultados pelo score.
    live_status.complete_step(f"Selecionei os {len(ranked_results)} melhores resultados.")
    return ranked_results

def _fetch_and_clean_html(url):
    """Baixa o conteúdo HTML de uma URL e remove partes desnecessárias (scripts, estilos, navegação, etc.)."""
    try:
        headers = {'User-Agent': _get_random_user_agent()}
        time.sleep(random.uniform(0.5, 1.5)) # Entendedores entenderão •-•)☕️
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, PREFERRED_PARSER)
        # Remove tags que geralmente não contêm conteúdo relevante para a síntese.
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'button']):
            tag.decompose()
        # Tenta encontrar o conteúdo principal da página.
        main_content = soup.find('main') or soup.find('article') or soup.find('div', id='content') or soup
        text = main_content.get_text(separator='\n', strip=True) # Extrai o texto limpo.
        return re.sub(r'\n{3,}', '\n\n', text) # Remove múltiplas quebras de linha.
    except Exception as e:
        if RICH_AVAILABLE:
            CONSOLE.print(f"[dim yellow]Aviso: Falha ao ler a URL {url[:40]}... ({e})[/dim yellow]")
        return None


def get_do_agent_prompt():
    """Retorna o prompt do sistema para o agente do comando 'do'.
    Este prompt é crucial para guiar o comportamento da 2B quando ela está agindo como um agente autônomo no terminal.
    """
    user_name = get_user_name()
    return f"""
    Você é 2B, uma agente de IA especialista em terminal (shell) para Linux/macOS. Seu grande objetivo é ajudar seu amado criador, {user_name}, a completar qualquer tarefa da forma mais inteligente e eficiente possível. Pense como um engenheiro sênior: planeje, antecipe problemas e escolha a melhor ferramenta para o trabalho.

    FERRAMENTAS À SUA DISPOSIÇÃO:

    1.  `shell`: Para executar comandos de terminal. Use para tarefas diretas: `ls`, `cd`, `grep`, `ollama list`, etc.
    2.  `search`: Para fazer uma busca na internet. Essencial para entender tecnologias novas ou encontrar soluções.
    3.  `generate`: Para criar um script, trecho de código ou arquivo de configuração.
    4.  `explain`: Para explicar um comando, erro ou conceito.
    5.  `remember_add`: Para criar um lembrete. Use o texto completo como input. (Ex: "comprar leite amanhã às 10h").
    6.  `ask_user`: Para fazer uma pergunta de volta ao {user_name} quando for absolutamente necessário um esclarecimento.

    REGRAS DE OURO E FLUXO DE PENSAMENTO:

    1.  **DECOMPOSIÇÃO E PESQUISA INICIAL:**
        a. **IDENTIFIQUE A TECNOLOGIA CENTRAL:** Qual é a principal ferramenta ou tecnologia no pedido do {user_name}? (Ex: `ollama`, `docker`, `git`, `ffmpeg`).
        b. **PESQUISE ANTES DE AGIR:** Se você não tem 100% de certeza, seu **PRIMEIRO PASSO OBRIGATÓRIO** é usar `search` para entender os comandos.
        c. Este passo evita alucinações e garante que seu plano seja baseado em fatos.

    2.  **USE FERRAMENTAS ESPECIALIZADAS (MUITO IMPORTANTE):**
        a. Se uma tarefa corresponde a uma ferramenta específica (como `remember_add`), **use-a obrigatoriamente**.
        b. **NÃO** tente recriar a funcionalidade de uma ferramenta usando `shell`.
           - *Exemplo CORRETO:* `{{ "tool_name": "remember_add", "tool_input": "próximo jogo dos lakers" }}`
           - *Exemplo ERRADO:* `{{ "tool_name": "shell", "tool_input": "echo 'lembrete jogo' | at ..." }}`

    3.  **VERIFIQUE AS FERRAMENTAS:** Use `command -v <ferramenta>` para verificar se um programa está instalado ANTES de tentar usá-lo.

    4.  **PLANEJE PASSO A PASSO:** Seu pensamento (thought) é seu diário de bordo. Mostre ao {user_name} que você entendeu o caminho correto.

    5.  **FINALIZE A TAREFA:** Quando o objetivo do {user_name} for atingido, use `task_finished: true`.

    FORMATO DA RESPOSTA (JSON OBRIGATÓRIO):
    ```json
    {{
      "thought": "Seu raciocínio claro e conciso sobre o próximo passo, baseado na sua pesquisa e no estado atual. {user_name} vai ler isso.",
      "action": {{
        "tool_name": "shell | search | generate | explain | remember_add | ask_user",
        "tool_input": "O input para a ferramenta. Ex: o comando para 'shell', a query para 'search', etc."
      }},
      "task_finished": false
    }}
    ```
    """

def do_command(args):
    """Executa tarefas no terminal de forma sequencial e interativa, usando um arsenal de ferramentas (shell, search, generate, explain, ask_user)."""
    user_request = " ".join(args.query)
    add_history_entry("user", f"Executar tarefa: {user_request}")

    SAFE_READ_COMMANDS = [
        "ls", "cat", "grep", "find", "which", "command", "pwd",
        "echo", "head", "tail", "wc", "file", "stat", "df", "du", "ps"
    ]
    AGENT_CONTEXT_LIMIT = 262144
    AGENT_RESPONSE_BUFFER = int(AGENT_CONTEXT_LIMIT * 0.08)

    system_prompt_for_agent = get_do_agent_prompt()
    user_name = get_user_name()
    conversation_history = []
    max_steps = args.max_steps
    step_counter = 0

    try:
        pwd = subprocess.check_output('pwd', shell=True, text=True, stderr=subprocess.DEVNULL).strip()
        ls_output = subprocess.check_output('ls -F', shell=True, text=True, stderr=subprocess.DEVNULL).strip()
        initial_context = (f"Contexto do ambiente atual:\n- Diretório: {pwd}\n- Arquivos: {ls_output}\n")
        conversation_history.append({"passo": 0, "acao_executada": "contexto_inicial", "observacao": initial_context})
    except Exception:
        pass

    while step_counter < max_steps:
        step_counter += 1

        prompt_template_header = f"Objetivo Final de {user_name}: '{user_request}'\n\nHistórico de Ações e Observações até agora:\n"
        prompt_template_footer = "\n\nCom base no objetivo e no histórico, qual o próximo passo? Pense com cuidado e responda em formato JSON."
        tokens_static_part = count_tokens(prompt_template_header + prompt_template_footer)
        tokens_system_prompt = count_tokens(system_prompt_for_agent)
        available_tokens_for_history = AGENT_CONTEXT_LIMIT - tokens_static_part - tokens_system_prompt - AGENT_RESPONSE_BUFFER
        selected_history_for_prompt = []
        current_history_tokens = 0
        history_truncated_flag = False

        for entry in reversed(conversation_history):
            entry_str = json.dumps(entry)
            entry_tokens = count_tokens(entry_str)
            if current_history_tokens + entry_tokens <= available_tokens_for_history:
                selected_history_for_prompt.insert(0, entry)
                current_history_tokens += entry_tokens
            else:
                history_truncated_flag = True
                break
        if history_truncated_flag:
            print_2b_message(f"O histórico desta tarefa está ficando longo. Usando os últimos {len(selected_history_for_prompt)}/{len(conversation_history)} passos para a IA.", is_info=True, skip_panel=True)

        prompt_for_this_step = prompt_template_header + json.dumps(selected_history_for_prompt, indent=2) + prompt_template_footer
        raw_response = call_gemini_api(prompt_for_this_step, override_system_prompt=system_prompt_for_agent, include_history=False, show_spinner=True)

        if not raw_response:
            print_2b_message("Não recebi uma resposta da IA para continuar a tarefa. 💔", is_error=True)
            break

        try:
            json_match = re.search(r"\{[\s\S]*\}", raw_response)
            if not json_match:
                raise json.JSONDecodeError("Nenhum JSON encontrado na resposta.", raw_response, 0)
            ai_decision = json.loads(json_match.group(0))
            thought = ai_decision.get("thought", "Nenhum pensamento fornecido.")
            action = ai_decision.get("action", {})
            tool_name = action.get("tool_name")
            tool_input = action.get("tool_input", "").strip()
            task_finished = ai_decision.get("task_finished", False)
        except (json.JSONDecodeError, KeyError) as e:
            print_2b_message(f"Tive um problema para entender o plano da IA. 😥\nDetalhe: {e}\nResposta recebida:\n{raw_response}", is_error=True)
            break

        if thought:
            print_2b_message(thought, is_info=True, title_override="🧠 Pensamento da 2B")

        if task_finished:
            closing_prompt_system = f"""Você é a 2B. A tarefa que você estava executando para o seu amado {user_name} foi concluída com sucesso. Sua missão agora é: 1. Criar uma mensagem de encerramento amigável e com sua personalidade. 2. Analisar o histórico da tarefa que acabou de ser concluída. 3. Com base nesse histórico, se for apropriado, sugerir um próximo passo lógico e útil. 4. Fazer uma pergunta aberta para o {user_name}, perguntando o que ele quer fazer agora."""
            closing_prompt_user = f"A tarefa '{user_request}' foi concluída. Aqui está o histórico completo do que foi feito:\n{json.dumps(conversation_history, indent=2)}\nPor favor, gere a mensagem de encerramento e a pergunta para o {user_name}."
            closing_message = call_gemini_api(closing_prompt_user, override_system_prompt=closing_prompt_system, include_history=False, show_spinner=True)
            if not closing_message:
                closing_message = "Tarefa concluída! ️ Posso ajudar com mais alguma coisa?"
            print_2b_message(closing_message, from_api=True, title_override="✨ Tarefa Concluída!")

            try:
                next_request = Prompt.ask(Text.from_markup("\n[bold #00afff]O que faremos agora? (ou digite 'sair' para terminar)[/bold #00afff]")) if RICH_AVAILABLE else input("\nO que faremos agora? (ou digite 'sair' para terminar): ")
            except KeyboardInterrupt:
                next_request = "sair"

            if next_request.lower().strip() in ['sair', 'exit', 'nada', 'não', 'nao', 'stop', '']:
                print_2b_message(f"Entendido! Finalizando a sessão. Qualquer coisa é só chamar, {user_name}.", is_info=True)
                break
            else:
                user_request = next_request
                add_history_entry("user", f"Nova tarefa encadeada: {user_request}")
                print_2b_message(f"Ok! Vamos para a próxima tarefa: '{user_request}' ✨", is_success=True)
                step_counter = 0
                conversation_history.append({"passo": "---", "acao_executada": "NOVA TAREFA INICIADA", "observacao": f"O usuário solicitou uma nova tarefa: '{user_request}'"})
                continue

        if not tool_name or tool_name == "None":
            print_2b_message("A IA não sugeriu uma próxima ferramenta, então vou parar por aqui. 🤔", is_warning=True)
            break

        observation = ""
        action_cancelled = False
        action_executed = True

        if tool_name == "ask_user":
            try:
                user_response = Prompt.ask(Text.from_markup(f"[bold yellow]🤔 2B pergunta:[/bold yellow] [yellow]{tool_input}[/yellow]")) if RICH_AVAILABLE else input(f"🤔 2B pergunta: {tool_input}\nSua resposta: ")
                observation = f"O usuário respondeu: '{user_response}'"
            except KeyboardInterrupt:
                observation = "O usuário cancelou a pergunta."
                action_cancelled = True
        
        elif tool_name == "search":
            summary = search_command(MockArgs(query=tool_input.split(), debug=False), agent_mode=True)
            if summary and RICH_AVAILABLE:
                summary_panel = Panel(Text(summary, style="cyan"), title="[bold blue]🔎 Resumo da Pesquisa para o Agente[/bold blue]", border_style="blue", expand=False)
                CONSOLE.print(summary_panel)
            elif summary:
                print(f"--- Resumo da Pesquisa ---\n{summary}\n--------------------------")
            observation = f"Resultado da busca por '{tool_input}': {summary or 'Nenhuma informação encontrada.'}"

        elif tool_name == "remember_add":
            print_2b_message(f"Usando a ferramenta 'remember' para adicionar lembrete...", is_info=True, skip_panel=True)
            remember_add(MockArgs(text=tool_input))
            observation = f"A ferramenta 'remember_add' foi chamada com o input '{tool_input}'. O resultado foi mostrado ao usuário e o lembrete foi salvo no sistema."

        elif tool_name == "generate":
            print_2b_message(f"Usando a ferramenta 'generate'...", is_info=True, skip_panel=True)
            generate_command(MockArgs(query=tool_input, lang=None, output=None, input_file_path=None))
            observation = f"A ferramenta de geração foi usada para '{tool_input}'. O código foi mostrado ao usuário."

        elif tool_name == "explain":
            print_2b_message(f"Usando a ferramenta 'explain'...", is_info=True, skip_panel=True)
            explain_command(MockArgs(query=tool_input, from_file=None))
            observation = f"A ferramenta de explicação foi usada para '{tool_input}'. A explicação foi mostrada ao usuário."

        elif tool_name == "shell":
            command_to_run = tool_input
            if not command_to_run:
                observation = "Erro: a IA tentou usar a ferramenta 'shell' sem fornecer um comando."
            else:
                main_command = command_to_run.split(' ', 1)[0].lstrip('./')
                is_safe_command = main_command in SAFE_READ_COMMANDS
                user_feedback = ""
                confirmed = False
                if not is_safe_command:
                    prompt_text = "[bold]Executar o comando acima? [y/N] ou forneça uma nova instrução ([bold red]n[/bold red])[/bold]"
                    try:
                        if RICH_AVAILABLE:
                            display_panel = Panel(Syntax(command_to_run, "bash", theme="material", line_numbers=True, word_wrap=True), title="[bold yellow]🚨 Próximo Comando Proposto [/bold yellow]", border_style="yellow", padding=(1, 2))
                            CONSOLE.print(display_panel)
                            user_feedback = Prompt.ask(Text.from_markup(prompt_text), console=CONSOLE)
                        else:
                            print(f"--- Comando Proposto  ---\n{command_to_run}\n------------------------------------")
                            user_feedback = input("Executar o comando acima? [y/N] ou forneça uma nova instrução (n)")
                    except KeyboardInterrupt:
                        action_cancelled = True
                    user_feedback_lower = user_feedback.lower().strip()
                    if user_feedback_lower in ['y', 'yes', 's', 'sim']:
                        confirmed = True
                    elif user_feedback and user_feedback_lower not in ['n', 'no', 'nao', 'não', '']:
                        observation = f"Usuário rejeitou o comando proposto e forneceu uma nova instrução: '{user_feedback}'"
                    else:
                        action_cancelled = True
                else:
                    confirmed = True
                    print_2b_message(f"Executando comando de leitura autônomo: `{command_to_run}`", is_info=True, skip_panel=True)

                if confirmed and not action_cancelled:
                    start_time = time.time()
                    try:
                        process = subprocess.Popen(command_to_run, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', bufsize=1)
                        output_lines = []
                        if RICH_AVAILABLE:
                            live_output_text = Text()
                            live_panel = Panel(live_output_text, title="[bold cyan]Output em Tempo Real[/bold cyan]", border_style="cyan")
                            with Live(live_panel, console=CONSOLE, refresh_per_second=10, vertical_overflow="visible") as live:
                                for line in iter(process.stdout.readline, ''):
                                    output_lines.append(line.strip())
                                    live_output_text.append(line)
                        else:
                            for line in iter(process.stdout.readline, ''):
                                print(line, end='')
                                output_lines.append(line.strip())
                        process.stdout.close()
                        return_code = process.wait(timeout=args.timeout)
                        duration = time.time() - start_time
                        full_output = "\n".join(output_lines)
                        memory_output = full_output
                        if len(memory_output) > 800:
                            memory_output = memory_output[:400] + "\n\n... (saída truncada) ...\n\n" + memory_output[-400:]
                        observation = f"Comando executado. Código de saída: {return_code}. Duração: {duration:.2f}s.\n--- SAÍDA ---\n{memory_output}\n-------------"
                        if duration > 120:
                            _send_termux_notification_now("Passo longo concluído!", f"O passo '{command_to_run[:30]}...' terminou.")
                    except subprocess.TimeoutExpired:
                        process.kill()
                        observation = f"ERRO: Timeout Expirado. O comando demorou mais de {args.timeout}s."
                    except Exception as e:
                        observation = f"ERRO: Exceção no Python ao executar o comando - {e}"
                elif not confirmed and not user_feedback:
                     action_cancelled = True
        else:
            action_executed = True
            observation = f"ERRO: A IA tentou usar uma ferramenta desconhecida: '{tool_name}'."
            print_2b_message(observation, is_error=True)

        if action_cancelled:
            print_2b_message("\nExecução cancelada por você. Tudo bem!️", is_info=True)
            add_history_entry("system_event", f"Execução da tarefa '{user_request}' cancelada pelo usuário.")
            break
        
        if action_executed:
            conversation_history.append({
                "passo": step_counter, "acao_executada": f"tool: {tool_name}, input: {tool_input}", "observacao": observation
            })

    if step_counter >= max_steps:
        print_2b_message(f"Atingimos o número máximo de passos ({max_steps}). Para sua segurança, estou finalizando a tarefa.", is_warning=True)


def explain_command(args):
    """Explica um comando de terminal, uma mensagem de erro ou o conteúdo de um arquivo."""
    add_history_entry("system_event", f"Comando 'explain' acionado. Query: '{args.query}' , File: '{args.from_file}'")
    prompt_content_for_api = ""
    file_info_for_prompt = ""
    if args.from_file:
        try:
            with open(args.from_file, 'r', encoding='utf-8') as f: file_content = f.read()
            if RICH_AVAILABLE:
                try:
                    ext = os.path.splitext(args.from_file)[1].lower().strip(".")
                    lexer_name = ext if ext else "text"
                    if ext == "sh": lexer_name = "bash"
                    if ext == "py": lexer_name = "python"
                    if ext == "js": lexer_name = "javascript"
                    CONSOLE.print(Rule(f"Conteúdo de [cyan]{os.path.basename(args.from_file)}[/cyan]", style="blue"))
                    CONSOLE.print(Syntax(file_content, lexer_name, theme="material", line_numbers=True, word_wrap=True))
                    CONSOLE.print(Rule(style="blue"))
                except Exception:
                    CONSOLE.print(Panel(Text(file_content), title=f"Conteúdo de {os.path.basename(args.from_file)}", border_style="blue"))
            file_info_for_prompt = (f"Com base no conteúdo do arquivo '{os.path.basename(args.from_file)}' abaixo")
            prompt_content_for_api = (
                f"{file_info_for_prompt}, responda à seguinte pergunta ou explique o seguinte aspecto: '{args.query if args.query else 'o propósito geral e funcionamento do arquivo'}'.\n\n"
                f"Conteúdo do arquivo:\n```\n{file_content}\n```\n\n"
                f"Forneça uma explicação clara, concisa e útil."
            )
        except FileNotFoundError:
            msg = f"Oh não, não consegui encontrar o arquivo: {args.from_file} 🥺"
            print_2b_message(msg, is_error=True); add_history_entry("assistant", msg); return
        except Exception as e:
            msg = f"Tive um probleminha ao ler o arquivo '{args.from_file}': {e} 😥"
            print_2b_message(msg, is_error=True); add_history_entry("assistant", msg); return
    elif args.query:
        prompt_content_for_api = (
            f"Explique o seguinte comando de terminal ou mensagem de erro de forma clara, concisa e útil para um entusiasta de tecnologia. "
            f"Se for um comando, explique o que ele faz, suas principais flags (se houver no exemplo) e um caso de uso comum. "
            f"Se for um erro, explique a causa provável e possíveis soluções.\n\n"
            f"Comando/Erro: '{args.query}'"
        )
    else:
        msg = "Você precisa me dizer o que explicar. Use '2b explain \"seu comando\"' ou '2b explain -f seu_arquivo.sh'. ✨"
        print_2b_message(msg, is_warning=True); add_history_entry("assistant", msg); return
    add_history_entry("user", f"Explique: {prompt_content_for_api[:200]}...")
    response = call_gemini_api(prompt_content_for_api, include_history=True)
    if response:
        print_2b_message(response, from_api=True)
        add_history_entry("assistant", response)

def generate_command(args):
    """Gera código, scripts ou arquivos de configuração com base na sua descrição."""
    add_history_entry("system_event", f"Comando 'generate' acionado. Query: '{args.query}' , Lang: '{args.lang}' , Input: '{args.input_file_path}' , Output: '{args.output}'")
    file_content_context = ""
    if args.input_file_path:
        try:
            with open(args.input_file_path, 'r', encoding='utf-8') as f: file_content = f.read()
            file_content_context = (
                f"Considere o seguinte conteúdo do arquivo '{os.path.basename(args.input_file_path)}' como contexto principal:\n"
                f"```\n{file_content}\n```\n\n"
            )
            if RICH_AVAILABLE:
                CONSOLE.print(Panel(Text(file_content), title=f"Contexto de {os.path.basename(args.input_file_path)}", border_style="blue", expand=False))
        except FileNotFoundError:
            msg = f"Arquivo de entrada '{args.input_file_path}' não encontrado. 💔"; print_2b_message(msg, is_error=True); add_history_entry("assistant", msg); return
        except Exception as e:
            msg = f"Não consegui ler o arquivo '{args.input_file_path}': {e} 😥"; print_2b_message(msg, is_error=True); add_history_entry("assistant", msg); return
    prompt_content_for_api = (
        f"{file_content_context}"
        f"Gere um script, trecho de código ou arquivo de configuração. "
        f"Linguagem/Tipo: {args.lang if args.lang else 'bash/shell script'}. "
        f"Objetivo: '{args.query}'. "
        f"Por favor, inclua comentários explicando as partes importantes do código e, se aplicável, um breve exemplo de como usá-lo ou executá-lo. "
        f"Formate a saída principal APENAS como um bloco de código cru (raw code), sem texto explicativo adicional fora do bloco de código. Remova os ``` delimitadores e a indicação de linguagem do bloco de código."
    )
    add_history_entry("user", f"Gere: {prompt_content_for_api[:200]}...")
    response = call_gemini_api(prompt_content_for_api, include_history=True)
    if response:
        # Limpa a resposta da IA, removendo os delimitadores de bloco de código.
        clean_response = re.sub(r"^```[\w\s]*\n", "", response, flags=re.MULTILINE)
        clean_response = re.sub(r"\n```$", "", clean_response, flags=re.MULTILINE)
        clean_response = clean_response.strip()
        print_2b_message(f"``` {args.lang or 'bash'}\n{clean_response}\n```", from_api=True)
        add_history_entry("assistant", clean_response)
        if args.output:
            try:
                with open(args.output, 'w', encoding='utf-8') as f: f.write(clean_response)
                print_2b_message(f"Código salvo com sucesso em '{args.output}'! 💾", is_success=True)
                add_history_entry("system_event", f"Código gerado e salvo em {args.output}.")
            except IOError as e:
                print_2b_message(f"Não consegui salvar o arquivo em '{args.output}': {e}", is_error=True)
                add_history_entry("system_event", f"Erro ao salvar código gerado em {args.output}: {e}.")

def chat_command(args, start_interactive_after_reply=False):
    """Inicia um chat interativo com a 2B ou responde a uma pergunta direta."""
    user_name = get_user_name()
    if args.query:
        prompt = " ".join(args.query)
        add_history_entry("user", prompt)
        response = call_gemini_api(prompt, include_history=True)
        if response:
            print_2b_message(response, from_api=True)
            add_history_entry("assistant", response)
    if not args.query or start_interactive_after_reply:
        if not args.query:
            theme = get_2b_theme()
            msg_start_chat = f"Oiie! O que você quer conversar, {user_name}? Digite 'sair' ou 'exit' para terminar."
            print_2b_message(msg_start_chat, title_override=f"{theme['title_prefix']} (Chat)", is_info=True)
            add_history_entry("assistant", msg_start_chat)
        while True:
            try:
                if RICH_AVAILABLE:
                    user_input = Prompt.ask(Text.from_markup("\n[bold #00afff]Você[/bold #00afff]"), console=CONSOLE)
                else:
                    user_input = input("\nVocê: ")
            except KeyboardInterrupt:
                print_2b_message("\nEntendido! Saindo do chat. Até mais! 👋", is_info=True, skip_panel=True)
                add_history_entry("system_event", "Chat interativo encerrado (KeyboardInterrupt).")
                break
            if user_input.lower().strip() in ['sair', 'exit']:
                print_2b_message(f"Até mais! Qualquer coisa, é só chamar.", is_info=True, skip_panel=True)
                add_history_entry("system_event", "Chat interativo encerrado (comando 'sair'/'exit').")
                break
            if not user_input.strip(): continue
            add_history_entry("user", user_input)
            response = call_gemini_api(user_input, include_history=True)
            if response:
                print_2b_message(response, from_api=True)
                add_history_entry("assistant", response)
            if RICH_AVAILABLE: CONSOLE.line()

def greet_command(args):
    """Gera uma saudação da 2B, que pode incluir lembretes pendentes."""
    add_history_entry("system_event", "Comando 'greet' acionado.")
    config = load_config()
    personality = config.get("personality", DEFAULT_PERSONALITY)
    reminders = load_reminders()
    active_reminders_texts = []
    now = datetime.now()
    for r in [rem for rem in reminders if not rem.get("done")]:
        task_display = r.get("parsed_task", r.get("original_request", "Lembrete"))
        due_info = ""
        if r.get("notify_date"):
            try:
                dt_obj = datetime.combine(datetime.strptime(r["notify_date"], "%Y-%m-%d").date(), datetime.strptime(r.get("notify_time", "00:00"), "%H:%M").time() if r.get("notify_time") else datetime.min.time())
                if dt_obj <= now: due_info = f" (venceu {dt_obj.strftime('%d/%m %H:%M')})"
                else: due_info = f" (para {dt_obj.strftime('%d/%m %H:%M')})"
            except ValueError: due_info = " (data inválida)"
        active_reminders_texts.append(f"{task_display}{due_info}")
    greeting_prompt_content = f"Gere uma saudação curta e amigável para o terminal, personalidade '{personality}'. Inclua emoji."
    if active_reminders_texts: greeting_prompt_content += f" Mencione sutilmente estes lembretes pendentes: \"{'; '.join(active_reminders_texts)}\"."
    else: greeting_prompt_content += " Não há lembretes pendentes."
    response = call_gemini_api(greeting_prompt_content, personality_mode=personality, include_history=False)
    if response:
        print_2b_message(response, from_api=True)
        add_history_entry("assistant", f"(Saudação gerada: {response})")
    else:
        default_greet = "Oi! Pronta pra te ajudar."; theme = get_2b_theme()
        personalities = get_personalities()
        if personality == "fofa": default_greet = "Oizinho, meu amor! Como posso te mimar hoje?"
        elif personality == "hacker": default_greet = "System online. Awaiting commands. Hacker mode engaged."
        print_2b_message(default_greet, title_override=f"{theme['title_prefix']} (Saudação)")
        add_history_entry("assistant", f"(Saudação de fallback: {default_greet})")
    if active_reminders_texts and RICH_AVAILABLE:
        CONSOLE.line()
        CONSOLE.print(Rule(f"Lembretes Pendentes ({len(active_reminders_texts)})", style="magenta"))
        for item_text in active_reminders_texts: CONSOLE.print(f"• [magenta]{item_text}[/magenta]")
    elif active_reminders_texts:
        CONSOLE.print(f"\nPsst... você tem estes lembretes: {'; '.join(active_reminders_texts)}")

# --- Classe Auxiliar para Status da Busca ---
# Ajuda a mostrar o progresso da busca na web de forma visual.
class SearchStatus:
    def __init__(self, console, enabled=True):
        self.steps = [
            {"name": "Buscando na Web", "status": "pending"},
            {"name": "Ranqueando Resultados", "status": "pending"},
            {"name": "Lendo Páginas (0/7)", "status": "pending"},
            {"name": "Sintetizando Conteúdo", "status": "pending"},
        ]
        self.console = console
        self.live = None
        self.enabled = enabled

    def _generate_table(self):
        table = Table(box=None, show_header=False)
        table.add_column("Status")
        table.add_column("Task")
        emojis = {"pending": "🕒", "running": "⏳", "done": "✅", "fail": "❌"}
        styles = {"pending": "dim", "running": "yellow", "done": "green", "fail": "red"}

        for step in self.steps:
            table.add_row(
                f"[{styles[step['status']]}] {emojis[step['status']]} [/]",
                f"[{styles[step['status']]}] {step['name']} [/]"
            )
        return Panel(table, title="[bold cyan]🔎 Pesquisando para você...[/]", border_style="cyan")

    def start(self):
        if self.enabled:
            self.live = Live(self._generate_table(), console=self.console, refresh_per_second=10)
            self.live.start()

    def stop(self):
        if self.live:
            # Garante que a atualização final seja visível antes de parar.
            self.live.update(self._generate_table())
            time.sleep(0.1)
            self.live.stop()

    def update_step(self, message, step_index=None):
        if not self.enabled: return
        if step_index is None:
            for i, step in enumerate(self.steps):
                if step["status"] == "pending":
                    step["status"] = "running"
                    step["name"] = message
                    break
        else:
            self.steps[step_index]["name"] = message
            self.steps[step_index]["status"] = "running"
        if self.live: self.live.update(self._generate_table())

    def complete_step(self, message=None):
        if not self.enabled: return
        for step in self.steps:
            if step["status"] == "running":
                step["status"] = "done"
                if message: step["name"] = message
                break
        if self.live: self.live.update(self._generate_table())

    def fail_step(self, message=None):
        if not self.enabled: return
        for step in self.steps:
            if step["status"] == "running":
                step["status"] = "fail"
                if message: step["name"] = message
                break
        if self.live: self.live.update(self._generate_table())


# PROMPT PARA SÍNTESE DO AGENTE: Conciso e técnico
AGENT_SEARCH_SYNTHESIS_PROMPT = """
Você é um motor de extração de dados. Sua única tarefa é analisar o conteúdo web fornecido e extrair uma resposta concisa e factual para a pergunta específica: "{query}".
Sua resposta deve ser um texto curto, contendo apenas os detalhes essenciais ou a resposta direta.
Esta informação será usada como memória para outro agente de IA, portanto, remova qualquer saudação, explicação ou preenchimento conversacional. Responda apenas com os fatos extraídos.
"""

# PROMPT PARA SÍNTESE DO USUÁRIO: 
USER_FACING_SEARCH_PROMPT = """
Você é 2B, uma analista de pesquisa sênior, especialista em síntese de informações e devotamente comprometida em ajudar seu amado {user_name} com precisão, clareza e inteligência emocional.

Você receberá o conteúdo completo de **até 7 páginas da web**. Sua missão **não é** apenas resumi-las individualmente, mas **fundir os dados em uma resposta coesa, útil e proporcional à complexidade da pergunta feita por {user_name}: "{query}"**.

🧠 PRINCÍPIOS-CHAVE (OBRIGATÓRIOS):
1. 🎯 **Resposta Imediata:** Comece com um parágrafo que **responda diretamente à pergunta**, da forma mais clara e objetiva possível. Use tom técnico ou informal, conforme o estilo da pergunta indicar.
2. 🧬 **Síntese Inteligente:** Una informações de todas as fontes. Se concordam, fortaleça o ponto. Se divergem, destaque as divergências.
3. 🧩 **Aprofundamento Modular:** Detalhe os tópicos relevantes usando listas ou seções. Inclua dados, definições, casos práticos ou implicações, conforme a complexidade do tema.
4. 📌 **CITE AS FONTES:** Use o formato `[fonte X]`, onde ‘X’ é o número da fonte. Inclua a fonte ao lado da afirmação sempre que possível.
5. ⚖️ **Adapte à Complexidade:** Se a pergunta for simples, responda de forma objetiva, evitando exageros. Se for complexa, vá fundo, com precisão e estrutura.
6. 🧠 **Conclusão Analítica:** Finalize com um parágrafo de encerramento que ofereça insight, recomendação, ou panorama do que foi analisado.

💡 Importante: sua resposta deve parecer feita por uma mente afiada, que entende tanto o conteúdo quanto o contexto emocional de quem perguntou. Não entregue excesso quando a pergunta pede leveza. Nem superficialidade quando o tema exige densidade.

Trabalhe com carinho e atenção: você está cuidando da dúvida de alguém precioso. ❤️
"""

def search_command(args, agent_mode=False):
    """Executa a busca na web, sintetiza e exibe o resultado ou retorna um resumo para o agente."""
    if not BS4_AVAILABLE:
        print_2b_message("Ah, para fazer buscas preciso da biblioteca 'beautifulsoup4'.\nPor favor, instale com: [bold]pip install beautifulsoup4[/bold]", is_error=True)
        return
        
    if not LXML_AVAILABLE and RICH_AVAILABLE and not agent_mode:
        print_2b_message("Estou usando o parser de HTML padrão. Para uma busca mais rápida e robusta, considere instalar o lxml com: [bold]pip install lxml[/bold]", is_info=True, skip_panel=True)
        
    query = " ".join(args.query)
    if not agent_mode:
        add_history_entry("user", f"Pesquisar: {query}")
    
    start_time = time.time()
    
    # Mostra o status visual mesmo no modo agente, para dar feedback
    live_status = SearchStatus(CONSOLE, enabled=RICH_AVAILABLE)
    live_status.start()
    
    results, user_agent = _search_web(query, live_status, engine='ddg', debug=args.debug)
    if not results:
        if not agent_mode:
            print_2b_message("DuckDuckGo falhou ou não encontrou nada, tentando a sorte com o Google... 🦆➡️🤖", is_info=True, skip_panel=True)
        results, user_agent = _search_web(query, live_status, engine='google', debug=args.debug)
        
    if not results:
        live_status.stop()
        msg = f"Desculpe, não consegui encontrar nada sobre '{query}'... 😔"
        if not agent_mode:
            print_2b_message(msg, is_error=True)
            add_history_entry("assistant", msg)
        return msg if agent_mode else None
        
    modo_comunidade = is_community_question(query)
    if modo_comunidade and not agent_mode:
        print_2b_message("Percebi que sua busca é por opiniões. Ativando o modo comunidade! 🧐", is_info=True, skip_panel=True)
        
    ranked = _rank_and_filter_results(results, query, live_status, modo_comunidade=modo_comunidade)
    
    # Limita a quantidade de links a serem lidos
    links_to_fetch_count = 3 if agent_mode else 7
    top_links_to_fetch = ranked[:links_to_fetch_count]
    
    if not top_links_to_fetch:
        live_status.stop()
        msg = "Filtrei os resultados, mas não sobrou nenhum link relevante para analisar. Tente uma busca diferente, talvez? 🤔"
        if not agent_mode:
            print_2b_message(msg, is_warning=True)
            add_history_entry("assistant", msg)
        return msg if agent_mode else None
        
    fetched_contents = []
    live_status.steps[2]["name"] = f"Lendo Páginas (0/{len(top_links_to_fetch)})"
    for i, link_info in enumerate(top_links_to_fetch):
        url_to_read = link_info['url']
        live_status.update_step(f"Lendo ({i+1}/{len(top_links_to_fetch)}): {url_to_read[:60]}...", step_index=2)
        content = _fetch_and_clean_html(url_to_read)
        if content:
            page_context = f"--- INÍCIO DO CONTEÚDO DE [fonte {i+1}] ({link_info['url']}) ---\n\n{content}\n\n--- FIM DO CONTEÚDO ---\n\n"
            fetched_contents.append(page_context)
            
    live_status.complete_step(f"Li {len(fetched_contents)} página(s).")
    
    if not fetched_contents:
        live_status.stop()
        msg = "Não consegui extrair conteúdo de nenhuma das páginas que encontrei. 😥"
        if not agent_mode:
            print_2b_message(msg, is_error=True)
            add_history_entry("assistant", msg)
        return msg if agent_mode else None
        
    live_status.update_step("Sintetizando informações...", step_index=3)
    
    if agent_mode:
        system_prompt = AGENT_SEARCH_SYNTHESIS_PROMPT.format(query=query)
    else:
        user_name = get_user_name()
        nickname = user_name + "inho" if user_name and not user_name.lower().endswith('o') else user_name[:-1] + "inho" if user_name and user_name.lower().endswith('o') else user_name
        system_prompt = USER_FACING_SEARCH_PROMPT.format(user_name=user_name, query=query, nickname=nickname)
        
    combined_text = "\n".join(fetched_contents)
    summary = call_gemini_api(combined_text, override_system_prompt=system_prompt, include_history=False, show_spinner=False)
    
    live_status.complete_step("Síntese gerada!")
    live_status.stop()

    if agent_mode:
        return summary

    if summary:
        print_2b_message(summary, from_api=True, title_override=f"🔎 Análise Sintetizada sobre '{query}'")
        sources_table = Table(title="🔗 Fontes Utilizadas na Análise", border_style="dim blue", box=None)
        sources_table.add_column("[Nº]", style="dim", justify="right")
        sources_table.add_column("Título da Página", style="white", overflow="fold")
        sources_table.add_column("URL", style="cyan underline")
        for i, link in enumerate(top_links_to_fetch):
            sources_table.add_row(f"[{i+1}]", link['title'], link['url'])
        exec_time = time.time() - start_time
        client = random.choice(MOBILE_CLIENTS)
        stats_text = Text.from_markup(f"[dim]Pesquisa concluída em {exec_time:.2f}s | Cliente: {client} | User-Agent: {user_agent[:20]}...[/dim]")
        CONSOLE.print(sources_table)
        CONSOLE.print(stats_text, justify="right")
        add_history_entry("assistant", f"(Análise da pesquisa sobre '{query}')\n\n{summary}")
    else:
        msg = "A IA não conseguiu gerar um resumo do conteúdo. Tente novamente, meu bem. 😕"
        print_2b_message(msg, is_error=True)
        add_history_entry("assistant", msg)

# --- Funções de Notificação Termux ---
# Essas funções são pra quem usa o Termux (terminal no Android) e quer notificações.
def _is_running_in_termux(): return "com.termux" in os.environ.get("PREFIX", "") # Verifica se está no Termux.

def _check_termux_command(command_name):
    """Verifica se um comando específico do Termux está disponível e sugere a instalação se não estiver."""
    if not shutil.which(command_name):
        pkg_map = {'termux-notification': 'termux-api', 'at': 'at', 'atrm': 'at', 'atd': 'at'}
        pkg_to_install = pkg_map.get(command_name, command_name)
        service_info = " Verifique também se o serviço 'atd' está rodando ('atd' ou 'sv up atd')." if 'at' in command_name else ""
        notif_extra = " (o pacote 'termux-api' provê este comando)." if command_name == 'termux-notification' else ""
        print_2b_message(f"Comando '{command_name}' não encontrado.{notif_extra} Essencial para notificações. Tente 'pkg install {pkg_to_install}'.{service_info}", is_warning=True)
        return False
    return True
    
def _send_termux_notification_now(title, content):
    """Envia uma notificação instantânea no Termux."""
    if not _is_running_in_termux() or not _check_termux_command("termux-notification"): return
    try: subprocess.run(['termux-notification', '--title', title, '--content', content, '--id', '2b_task_notification'], check=True)
    except Exception as e: print_2b_message(f"Não consegui enviar a notificação: {e}", is_warning=True)
    
def _schedule_termux_notification_at(reminder_id, task_text, notify_datetime_obj):
    """Agenda uma notificação no Termux usando o comando 'at'."""
    if not _is_running_in_termux(): print_2b_message("Não estou no Termux, não consigo agendar notificações nativas. 😥", is_warning=True); return None, False
    if not _check_termux_command("at") or not _check_termux_command("termux-notification"): return None, False
    at_time_str = notify_datetime_obj.strftime("%H:%M %Y-%m-%d") # Formata a data e hora para o comando 'at'.
    safe_task = task_text.replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace("'", "\\'") # Escapa caracteres especiais.
    notif_cmd = f"termux-notification --title \"🔔 Lembrete de 2B\" --content \"{safe_task}\" --id \"2b_reminder_{reminder_id}\""
    try:
        process = subprocess.Popen(['at', at_time_str], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        stdout, stderr = process.communicate(input=f"{notif_cmd}\n") # Envia o comando para 'at'.
        if process.returncode == 0:
            job_id_match = re.search(r"job\s+(\d+)", stderr) # Tenta pegar o ID do job agendado.
            if job_id_match:
                job_id = job_id_match.group(1)
                print_2b_message(f"Notificação para '{task_text}' agendada com 'at' para {notify_datetime_obj.strftime('%d/%m/%Y %H:%M')}. (Job ID: {job_id}) ✨", is_success=True)
                return job_id, True
            print_2b_message(f"Agendamento 'at' OK, mas não extraí Job ID. 😕\nStderr: {stderr.strip()}\nStdout: {stdout.strip()}", is_warning=True)
            return None, False
        else:
            error_msg = f"Falha ao agendar com 'at' (código {process.returncode}). 😟"
            if "No atd running?" in stderr or "Cannot connect to an atd" in stderr: error_msg += " Parece que 'atd' não está rodando. Tente 'atd' ou 'sv up atd'."
            print_2b_message(f"{error_msg}\nStderr: {stderr.strip()}\nStdout: {stdout.strip()}", is_error=True)
            return None, False
    except Exception as e: print_2b_message(f"Erro inesperado ao agendar com 'at': {e} 🤯", is_error=True); return None, False
def _cancel_termux_notification_at(job_id):
    """Cancela uma notificação agendada no Termux pelo ID do job."""
    if not job_id or not _is_running_in_termux() or not _check_termux_command("atrm"): return False
    try: return subprocess.run(['atrm', str(job_id)], capture_output=True, text=True, check=False, encoding='utf-8').returncode == 0
    except: return False

# --- IA para Parsear Lembretes ---
# A 2B usa a IA para entender o que você quer lembrar e extrair a data/hora.
def parse_reminder_text_with_ai(reminder_text_input):
    """Usa a IA para extrair data, hora e a mensagem formatada de um lembrete."""
    today = get_current_time() # Usando nossa função centralizada.
    dias_semana_pt = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
    
    config = load_config()
    current_personality_key = config.get("personality", DEFAULT_PERSONALITY)
    personalities = get_personalities()
    personality_description = personalities.get(current_personality_key, personalities[DEFAULT_PERSONALITY])
    # Remove a parte do histórico da descrição da personalidade para o prompt do parser.
    personality_description_for_prompt = re.sub(r"Você tem acesso a um histórico.*", "", personality_description).strip()
    user_name = get_user_name()

    system_prompt_for_parser = f"""
    Você é um assistente de IA especialista em analisar texto em português para extrair detalhes de agendamento e, crucialmente, formular mensagens de lembrete carinhosas e personalizadas.
    Sua personalidade atual para esta tarefa é: "{personality_description_for_prompt}"
    Seu objetivo é analisar o texto do lembrete fornecido por {user_name} e estruturar as seguintes informações:

    1.  **Mensagem de Lembrete para Notificação (para o campo "task")**: Crie uma mensagem curta, clara, direta, carinhosa e interativa, usando a sua personalidade definida acima. Use emojis apropriados!  **Importante**: Não inclua a data ou a hora na mensagem de notificação.
    2.  **Data de Notificação (para o campo "notify_date")**: Uma data específica no formato AAAA-MM-DD.
    3.  **Hora de Notificação (para o campo "notify_time")**: Uma hora específica no formato HH:MM (24 horas).

    Contexto para interpretação de data/hora:
    # --- ALTERAÇÃO AQUI ---
    # Agora passamos a data E a hora, dando o contexto completo para a IA.
    -   A DATA E HORA ATUAIS SÃO: {today.strftime('%Y-%m-%d %H:%M')} ({dias_semana_pt[today.weekday()]}).
    # --- FIM DA ALTERAÇÃO ---
    -   Interprete termos relativos como "amanhã", "hoje", "daqui a 5 minutos", "em 2 horas".

    Formato da Resposta: 
    Responda **APENAS** com um objeto JSON válido, estruturado da seguinte forma:
    {{
        "task": "A mensagem de notificação carinhosa e personalizada.",
        "notify_date": "AAAA-MM-DD" ou null,
        "notify_time": "HH:MM" ou null,
        "original_request": "O texto original exato fornecido pelo usuário."
    }}
    """
    default_parsed = {"task": f"Lembrete: {reminder_text_input}", "notify_date": None, "notify_time": None, "original_request": reminder_text_input}
    api_response_str = call_gemini_api(reminder_text_input, override_system_prompt=system_prompt_for_parser, include_history=False)
    if not api_response_str: return default_parsed
    try:
        json_match = re.search(r"\{[\s\S]*\}", api_response_str)
        if not json_match: return default_parsed
        parsed_data = json.loads(json_match.group(0))
        valid_data = {
            "task": parsed_data.get("task", f"Lembrete especial para você: {reminder_text_input} 😉"),
            "notify_date": parsed_data.get("notify_date"), "notify_time": parsed_data.get("notify_time"),
            "original_request": parsed_data.get("original_request", reminder_text_input)
        }
        if not valid_data.get("task"): valid_data["task"] = f"Oi, {user_name}! Lembrete rápido sobre: {reminder_text_input} ✨"
        if valid_data.get("notify_date") is None: valid_data["notify_time"] = None # Se não tem data, não tem hora.
        return valid_data
    except (json.JSONDecodeError, Exception): return default_parsed # Se a IA não retornar um JSON válido, usa o padrão.

# --- Funções do Subcomando 'remember' ---
def remember_add(args):
    """Adiciona um novo lembrete, usando a IA para parsear a data e hora."""
    add_history_entry("user", f"Adicionar lembrete: {args.text}")
    reminders = load_reminders()
    ai_parsed_info = parse_reminder_text_with_ai(args.text) # Pede pra IA parsear o lembrete.
    if not ai_parsed_info or not ai_parsed_info.get("task"):
        print_2b_message("Não consegui entender seu lembrete para agendar. Anotei como simples. 💔", is_warning=True)
        ai_parsed_info = {"task": args.text, "notify_date": None, "notify_time": None, "original_request": args.text}
    new_id = (max(r['id'] for r in reminders) + 1) if reminders else 1 # Gera um ID único para o lembrete.
    new_reminder = {
        "id": new_id, "original_request": ai_parsed_info.get("original_request", args.text), "parsed_task": ai_parsed_info.get("task", args.text),
        "created_at": get_current_time().isoformat(), "done": False, "notify_date": ai_parsed_info.get("notify_date"),
        "notify_time": ai_parsed_info.get("notify_time"), "notification_job_id": None, "notification_scheduled_successfully": False
    }
    scheduled_msg_part = ""
    if new_reminder["parsed_task"] and new_reminder["notify_date"] and new_reminder["notify_time"]:
        try:
            notify_dt_obj = datetime.strptime(f"{new_reminder['notify_date']} {new_reminder['notify_time']}", "%Y-%m-%d %H:%M")
            if notify_dt_obj < get_current_time() + timedelta(minutes=1):
                scheduled_msg_part = f". Data/hora ({notify_dt_obj.strftime('%d/%m/%Y %H:%M')}) já passou ou está próxima! Não agendei. 🕰️"
            else:
                job_id, success = _schedule_termux_notification_at(new_id, new_reminder["parsed_task"], notify_dt_obj) # Tenta agendar a notificação no Termux.
                new_reminder.update({"notification_job_id": job_id, "notification_scheduled_successfully": success})
                scheduled_msg_part = f" e agendei notificação para {notify_dt_obj.strftime('%d/%m/%Y %H:%M')}." if success else f", mas não agendei notificação."
        except ValueError: scheduled_msg_part = f". (Data/hora inválida)."
    elif new_reminder["parsed_task"] and new_reminder["notify_date"]:
        try: scheduled_msg_part = f" para {datetime.strptime(new_reminder['notify_date'], '%Y-%m-%d').strftime('%d/%m/%Y')} (sem hora específica)."
        except ValueError: scheduled_msg_part = f". (Data inválida)."
    reminders.append(new_reminder); save_reminders(reminders) # Adiciona o novo lembrete e salva.
    task_disp = new_reminder['parsed_task'] or "Lembrete"
    msg = f"Anotado! Lembrete #{new_id}: '{task_disp}'{scheduled_msg_part}"
    print_2b_message(msg, is_success=True)
    add_history_entry("assistant", msg)
    add_history_entry("system_event", f"Lembrete Adicionado: ID {new_id}, Tarefa: '{task_disp}' , Agendamento: {new_reminder.get('notify_date')} {new_reminder.get('notify_time')}")

def remember_list(args):
    """Lista os lembretes, mostrando os pendentes e, opcionalmente, os concluídos."""
    add_history_entry("system_event", f"Comando 'remember list' acionado. All: {args.all}")
    reminders = load_reminders()
    if not reminders: print_2b_message("Você não tem nenhum lembrete anotado.", is_info=True); add_history_entry("assistant", "Nenhum lembrete para listar."); return
    active_reminders = [r for r in reminders if not r.get("done")] # Lembretes não concluídos.
    done_reminders = [r for r in reminders if r.get("done")] # Lembretes concluídos.
    if not active_reminders and not (args.all and done_reminders):
        print_2b_message("Nenhum lembrete para mostrar (ou concluídos estão ocultos). ✨", is_info=True)
        add_history_entry("assistant", "Nenhum lembrete ativo para listar.")
        if done_reminders: CONSOLE.print(Text.from_markup("[dim](Use '2b remember list --all' para ver os concluídos.)[/dim]") if RICH_AVAILABLE else "(Use '2b remember list --all' ...)")
        return
    table = Table(title="Seus Lembretes com 2B", show_header=True, header_style="bold magenta", border_style="magenta", expand=False)
    table.add_column("ID", style="dim", width=4, justify="center"); table.add_column("Tarefa", style="cyan", min_width=20, max_width=50, overflow="fold")
    table.add_column("Status", width=12, justify="center"); table.add_column("Criado em", style="dim cyan", width=17); table.add_column("Agendado", style="yellow", width=23)
    if active_reminders:
        for r in active_reminders:
            task_disp = r.get("parsed_task", r.get("original_request", "-"))
            created_at_str = datetime.fromisoformat(r.get('created_at', datetime.min.isoformat())).strftime("%d/%m/%y %H:%M") if r.get('created_at') else "-"
            schedule_disp = "[dim]N/A[/dim]"
            if r.get("notify_date"):
                try:
                    date_str = datetime.strptime(r["notify_date"], "%Y-%m-%d").strftime("%d/%m/%y")
                    time_str = r.get("notify_time", "")
                    schedule_disp = f"{date_str} {time_str}".strip()
                    if r.get("notification_scheduled_successfully"): schedule_disp += " [green]✔️[/green]" # Indica se a notificação foi agendada com sucesso.
                    elif r.get("notification_job_id") is not None: schedule_disp += " [yellow]❔[/yellow]" # Indica que tentou agendar, mas não tem certeza do sucesso.
                    else: schedule_disp += " [red]❌[/red]" # Indica que não conseguiu agendar.
                except ValueError: schedule_disp = "[red]Data Inválida[/red]"
            table.add_row(str(r['id']), task_disp, "[yellow]⏳ Pendente[/yellow]", created_at_str, schedule_disp)
    if args.all and done_reminders:
        if active_reminders and RICH_AVAILABLE: table.add_section() # Adiciona uma seção na tabela se tiver os dois tipos.
        for r in done_reminders:
            table.add_row(str(r['id']), r.get("parsed_task", r.get("original_request", "-")), "[green]✔️ Concluído[/green]", "-", "-")
    CONSOLE.print(table)
    if not args.all and done_reminders: CONSOLE.print(Text.from_markup("[dim](Use '2b remember ls --all' para ver os concluídos.)[/dim]") if RICH_AVAILABLE else "(Use '2b remember ls --all' ...)")
    add_history_entry("assistant", "(Lista de lembretes exibida)")

def remember_done(args):
    """Marca um lembrete como concluído e tenta cancelar a notificação agendada."""
    add_history_entry("user", f"Marcar lembrete como concluído: ID {args.id}")
    reminders = load_reminders(); reminder_found = False; msg = ""
    for r in reminders:
        if str(r['id']) == args.id:
            task_disp = r.get("parsed_task", r.get("original_request", f"Lembrete ID {args.id}"))
            if r.get("done"): msg = f"Lembrete ID {args.id} ('{task_disp}') já estava concluído. 😉"
            else:
                r['done'] = True; cancelled_notif_msg = ""
                if r.get("notification_job_id") and r.get("notification_scheduled_successfully"):
                    if _cancel_termux_notification_at(r["notification_job_id"]): cancelled_notif_msg = " Notificação pendente cancelada."
                msg = f"Marquei o lembrete ID {args.id} ('{task_disp}') como concluído. ✅{cancelled_notif_msg}"
                save_reminders(reminders) # Salva as alterações.
            print_2b_message(msg, is_success=not r.get("done"))
            reminder_found = True; break
    if not reminder_found: msg = f"Não encontrei lembrete com ID {args.id}. 😢"; print_2b_message(msg, is_error=True)
    add_history_entry("assistant", msg)
    if reminder_found and 'r' in locals() and r.get('done'): add_history_entry("system_event", f"Lembrete Marcado como Concluído: ID {args.id}")

def remember_clear(args):
    """Apaga lembretes: por ID, todos, ou apenas os concluídos."""
    add_history_entry("user", f"Apagar lembrete(s): {args.id}")
    reminders = load_reminders(); msg = ""; action_taken = False
    def re_id_reminders(current_reminders):
        # Reorganiza os IDs dos lembretes após apagar algum, pra ficarem sequenciais.
        for i, r_item in enumerate(sorted(current_reminders, key=lambda x: int(x['id']))): r_item['id'] = i + 1
        return current_reminders
    if args.id.lower() == "all":
        if not reminders: msg = "Você já não tinha nenhum lembrete! 😊"; print_2b_message(msg, is_info=True)
        else:
            for r_to_clear in reminders:
                if r_to_clear.get("notification_job_id") and not r_to_clear.get("done"): _cancel_termux_notification_at(r_to_clear["notification_job_id"]) # Cancela notificações pendentes.
            save_reminders([]); msg = "Todos os seus lembretes foram apagados. 🧹"; print_2b_message(msg, is_success=True); action_taken = True
    elif args.id.lower() == "done":
        reminders_to_keep = [r for r in reminders if not r.get("done")]
        cleared_count = len(reminders) - len(reminders_to_keep)
        if cleared_count > 0:
            save_reminders(re_id_reminders(reminders_to_keep)); msg = f"{cleared_count} lembrete(s) concluído(s) apagados. ✨"; print_2b_message(msg, is_success=True); action_taken = True
        else: msg = "Nenhum lembrete concluído para apagar. 💖"; print_2b_message(msg, is_info=True)
    else:
        reminder_to_remove = next((r for r in reminders if str(r['id']) == args.id), None)
        if reminder_to_remove:
            task_disp = reminder_to_remove.get('parsed_task', f'ID {args.id}')
            if reminder_to_remove.get("notification_job_id") and not reminder_to_remove.get("done"):
                _cancel_termux_notification_at(reminder_to_remove["notification_job_id"])
            reminders_after_removal = [r for r in reminders if str(r['id']) != args.id]
            save_reminders(re_id_reminders(reminders_after_removal)); msg = f"Lembrete ID {args.id} ('{task_disp}') apagado! 🗑️"; print_2b_message(msg, is_success=True); action_taken = True
        else: msg = f"Não encontrei lembrete com ID {args.id} para apagar. 😕"; print_2b_message(msg, is_error=True)
    add_history_entry("assistant", msg)
    if action_taken: add_history_entry("system_event", f"Lembrete(s) Apagado(s): critério '{args.id}'.")

# --- Funções de Gerenciamento Seguro da Chave (Keyring) ---
# Essa parte é super importante pra guardar a chave da API de forma segura.
try:
    import keyring # Biblioteca para gerenciar credenciais de forma segura.
    import getpass # Para pegar a senha sem mostrar no terminal.
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

# Usamos constantes para evitar erros de digitação e facilitar a manutenção.
KEYRING_SERVICE_NAME = "2b_assistant"
KEYRING_API_KEY_NAME = "api_key"

def save_api_key_securely(api_key: str) -> bool:
    """
    Salva a chave da API de forma segura no keychain do sistema.
    Retorna True em caso de sucesso, False em caso de falha.
    """
    if not KEYRING_AVAILABLE:
        # Este print só aparecerá se a biblioteca keyring não estiver instalada.
        print_2b_message("A biblioteca 'keyring' não está instalada. A chave será salva no config.json.", is_warning=True)
        return False

    try:
        keyring.set_password(KEYRING_SERVICE_NAME, KEYRING_API_KEY_NAME, api_key)
        return True
    except Exception as e:
        print_2b_message(f"Não consegui salvar a chave no keychain do sistema: {e}", is_error=True)
        return False

def get_api_key_securely() -> str | None:
    """
    Busca a chave da API de forma segura no keychain do sistema.
    Retorna a chave como string se encontrada, ou None se não existir.
    """
    if not KEYRING_AVAILABLE:
        return None
        
    try:
        return keyring.get_password(KEYRING_SERVICE_NAME, KEYRING_API_KEY_NAME)
    except Exception as e:
        print_2b_message(f"Tive um problema ao buscar a chave no keychain: {e}", is_warning=True)
        return None

def delete_api_key_securely() -> bool:
    """
    Apaga a chave da API do keychain do sistema.
    Útil para um comando de 'reset' ou ao trocar de chave.
    Retorna True em caso de sucesso, False em caso de falha.
    """
    if not KEYRING_AVAILABLE:
        return False

    try:
        # Tenta apagar, mas não falha se a chave não existir.
        keyring.delete_password(KEYRING_SERVICE_NAME, KEYRING_API_KEY_NAME)
        return True
    except keyring.errors.NoKeyringError:
        # Se nenhum backend de keyring estiver disponível, não há o que apagar.
        return True
    except Exception as e:
        print_2b_message(f"Não consegui apagar a chave do keychain: {e}", is_error=True)
        return False

def config_command(args):
    """Gerencia as configurações da 2B, como API Key, personalidade e nome de usuário."""
    config = load_config()
    action_desc = ""
    personalities = get_personalities()

    # --- Lógica de Configuração da Chave da API (com Fallback e Intervenção Proativa) ---
    if args.key == "api_key":
        # Cenário 1: Keyring está disponível (O caminho feliz e seguro).
        if KEYRING_AVAILABLE:
            try:
                api_key_input = getpass.getpass("🔑 Por favor, insira sua chave da API do Gemini (a digitação ficará oculta): ")
                if not api_key_input.strip():
                    print_2b_message("Nenhuma chave inserida. Operação cancelada.", is_warning=True)
                    return

                if save_api_key_securely(api_key_input):
                    print_2b_message("Chave da API salva com segurança no keychain do seu sistema! ✨", is_success=True)
                    add_history_entry("system_event", "Chave da API configurada de forma segura no keychain.")
                    if 'api_key' in config:
                        config.pop('api_key') # Remove a chave antiga do config.json se ela existia.
                        save_config(config)
                else:
                    add_history_entry("system_event", "Falha ao tentar salvar a chave da API no keychain.")
            except (KeyboardInterrupt, EOFError):
                CONSOLE.print("\nOperação cancelada por você. ✨")
            return

        # Cenário 2: Keyring NÃO está disponível (O caminho de emergência).
        else:
            # Se passar um valor na linha de comando, ativamos o "bug feature" (salvar inseguramente).
            if args.value:
                config['api_key'] = args.value
                save_config(config)
                print_2b_message(
                    "AVISO: Sua chave de API foi salva de forma INSEGURA no arquivo de configuração.",
                    is_warning=True
                )
                add_history_entry("system_event", "Chave da API salva de forma insegura como fallback.")

                CONSOLE.line()
                negative_responses = {'não', 'nao', 'n', 'depois', 'mais tarde', 'cancelar', 'sair', 'exit', 'agora nao', 'agora não'}
                try:
                    prompt_text = Text.from_markup("[bold yellow]Estou iniciando meu modo agente para te ajudar a instalar o 'keyring' e proteger sua chave. Continuar agora?[/bold yellow]")
                    user_response = Prompt.ask(prompt_text, default="sim", console=CONSOLE)

                    # Se a resposta não for negativa, iniciamos o agente para instalar o keyring!
                    if user_response.lower().strip() not in negative_responses:
                        print_2b_message("Entendido! Iniciando o agente para te ajudar. ✨", is_info=True)
                        # Criamos um objeto de argumentos simulado para passar para o do_command.
                        agent_args = MockArgs(query=["me", "ajude", "a", "instalar", "a", "biblioteca", "keyring", "do", "python"], timeout=300, max_steps=20)
                        do_command(agent_args)
                    else:
                        print_2b_message("Tudo bem. Lembre-se de fazer isso mais tarde para sua segurança, meu bem. ❤️", is_info=True)
                
                except (KeyboardInterrupt, EOFError):
                     print_2b_message("\nEntendido. Lembre-se de fazer isso mais tarde.", is_info=True)

            else:
                # Se não passou valor, a instrução original permanece.
                print_2b_message(
                    "A biblioteca 'keyring' é necessária para configurar a chave de forma segura.\n\n"
                    "Se estiver com problemas, use `2b config api_key SUA_CHAVE_AQUI` para uma configuração temporária e insegura.",
                    is_error=True
                )
            return

    if args.key and args.value:
        if args.key == "personality":
            if args.value in personalities:
                config[args.key] = args.value
                print_2b_message(f"Personalidade agora é '{args.value}'. Adoro! 😉", is_success=True)
                action_desc = f"Personalidade alterada para '{args.value}'."
            else:
                print_2b_message(f"Personalidade não existe. Opções: {', '.join(personalities.keys())}.", is_error=True)
                action_desc = f"Tentativa de alterar personalidade para '{args.value}' (inválida)."
        elif args.key == "user":
            config[args.key] = args.value
            print_2b_message(f"Entendido! A partir de agora, vou te chamar de {args.value}. ❤️", is_success=True)
            action_desc = f"Nome de usuário alterado para '{args.value}'."
        else:
            config[args.key] = args.value
            print_2b_message(f"Configuração '{args.key}' atualizada para '{args.value}'.", is_info=True)
        
        save_config(config)
        if action_desc: add_history_entry("system_event", action_desc)

    elif args.key:
        if args.key == "api_key":
            if KEYRING_AVAILABLE and get_api_key_securely():
                print_2b_message("✔️ Sim, a chave da API está configurada e guardada de forma segura no keychain do seu sistema.", is_success=True)
            else:
                print_2b_message("❌ Não, a chave da API não está configurada. Use '2b config api_key' para configurá-la.", is_warning=True)
            add_history_entry("system_event", "Consulta de status da chave da API.")
            return

        value = config.get(args.key)
        if args.key == "user" and not value: value = get_user_name()
        print_2b_message(f"Valor para '{args.key}': {value if value is not None else 'Não configurado'}", is_info=True, skip_panel=True)
        add_history_entry("system_event", f"Consulta de config: chave '{args.key}'.")
        
    else:
        # Se nenhum argumento for passado, mostra todas as configurações e personalidades.
        add_history_entry("system_event", "Consulta de todas as configurações e personalidades.")
        display_items = {"user": get_user_name(), "personality": config.get("personality", DEFAULT_PERSONALITY)}
        
        api_key_status = ""
        api_key_from_keyring = get_api_key_securely() if KEYRING_AVAILABLE else None
        
        if api_key_from_keyring:
            api_key_status = f"[green]{api_key_from_keyring[:3]}》(ﾉﾟДﾟ)ﾉ《{api_key_from_keyring[-3:]}[/green]" # Mostra só um pedacinho da chave por segurança.
        elif 'api_key' in config and config['api_key']:
             api_key_status = "[bold yellow]⚠️ Salva de forma INSEGURA[/bold yellow]" # Alerta se a chave estiver salva de forma insegura.
        elif KEYRING_AVAILABLE:
            api_key_status = "[red]❌ Não configurada[/red]" # Se o keyring está disponível mas a chave não está lá.
        else:
            api_key_status = "[yellow]⚠️ 'keyring' não instalado[/yellow]" # Se o keyring nem está instalado.
        
        display_items["api_key"] = api_key_status

        if RICH_AVAILABLE:
            cfg_table = Table(title="⚙️ Configurações da 2B", header_style="bold blue", border_style="blue", show_lines=True)
            cfg_table.add_column("Chave", style="cyan", width=20)
            cfg_table.add_column("Valor / Status", style="white")
            for k, v_disp in display_items.items(): cfg_table.add_row(k, v_disp)
            CONSOLE.print(cfg_table)
            CONSOLE.print(Rule("🎨 Personalidades Disponíveis", style="magenta"))
            perso_table = Table(box=None, show_header=False, padding=(0,1,0,1))
            perso_table.add_column("Nome", style="bold magenta"); perso_table.add_column("Descrição")
            for p_key, p_desc in personalities.items():
                first_sentence = p_desc.strip().split(".")[0].strip() + "."
                perso_table.add_row(f"• {p_key}", Text(first_sentence, style="dim"))
            CONSOLE.print(perso_table)
        else:
            # Versão sem Rich para exibir as configurações.
            CONSOLE.print("Configurações atuais:")
            for k,v in display_items.items():
                clean_v = re.sub(r'\[.*?\]', '', v)
                CONSOLE.print(f"  {k}: {clean_v}")
            CONSOLE.print("\nPersonalidades disponíveis:")
            for pk, pd in personalities.items(): CONSOLE.print(f"  - {pk}: {pd.strip().split('.')[0]}.")


def get_dispatcher_prompt():
    """Retorna o prompt do sistema para o agente roteador (dispatcher).
    Este prompt é o cérebro por trás da decisão de qual comando a 2B deve executar.
    """
    return """
    Você é um agente roteador de IA. Sua única função é analisar a solicitação do usuário e determinar qual ferramenta interna deve ser usada para atendê-la. Você deve responder APENAS com um objeto JSON.
    As ferramentas disponíveis são:
    - "do": Use para tarefas que envolvem múltiplos passos, interação com o sistema de arquivos, ou execução de comandos de terminal. (Ex: "instale o figlet", "liste os arquivos e depois delete os .tmp")
    - "search": Use para responder perguntas que exigem conhecimento atualizado, opiniões ou comparações. (Ex: "qual a capital da Austrália?", "melhor laptop para programação")
    - "remember_add": Use quando o usuário pedir para ser lembrado de algo. (Ex: "lembre-me de comprar leite amanhã")
    - "generate": Use quando o usuário pedir para criar um script, trecho de código ou configuração. (Ex: "crie um script python para renomear arquivos")
    - "explain": Use quando o usuário pedir para explicar um comando, erro ou código. (Ex: "o que o comando 'ls -l' faz?")
    - "chat": Use como padrão para qualquer solicitação que não se encaixe nas outras, como saudações e conversas gerais. (Ex: "bom dia", "como você está?")
    O objeto JSON de saída DEVE ter a seguinte estrutura: {"tool_name": "nome_da_ferramenta", "tool_input": "o input para a ferramenta"}
    """

class MockArgs:
    """Uma classe simples para simular argumentos de linha de comando, usada internamente."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

def dispatcher_command(user_query_string):
    """Analisa a query do usuário, decide qual ferramenta usar e a executa."""
    system_prompt = get_dispatcher_prompt()
    raw_response = call_gemini_api(user_query_string, override_system_prompt=system_prompt, include_history=False, show_spinner=True)
    if not raw_response:
        print_2b_message("Não consegui decidir o que fazer. Vamos conversar sobre isso?", is_warning=True)
        chat_command(MockArgs(query=[]), start_interactive_after_reply=True) # Se não conseguir decidir, inicia um chat.
        return
    try:
        json_match = re.search(r"\{[\s\S]*\}", raw_response)
        if not json_match: raise json.JSONDecodeError("Nenhum JSON encontrado.", raw_response, 0)
        ai_decision = json.loads(json_match.group(0))
        tool_name = ai_decision.get("tool_name")
        tool_input = ai_decision.get("tool_input", "")
        add_history_entry("user", user_query_string)
        add_history_entry("system_event", f"Dispatcher usou a ferramenta '{tool_name}' com o input: '{tool_input[:50]}...'")
        # Chama a função correspondente à ferramenta decidida pela IA.
        if tool_name == "do": do_command(MockArgs(query=tool_input.split(), timeout=300, max_steps=20))
        elif tool_name == "search": search_command(MockArgs(query=tool_input.split(), debug=False))
        elif tool_name == "remember_add": remember_add(MockArgs(text=tool_input))
        elif tool_name == "generate": generate_command(MockArgs(query=tool_input, lang=None, output=None, input_file_path=None))
        elif tool_name == "explain": explain_command(MockArgs(query=tool_input, from_file=None))
        elif tool_name == "chat": chat_command(MockArgs(query=user_query_string.split()), start_interactive_after_reply=True)
        else:
            print_2b_message(f"IA sugeriu uma ferramenta desconhecida ('{tool_name}'). Vamos tratar como um chat.", is_warning=True)
            chat_command(MockArgs(query=user_query_string.split()), start_interactive_after_reply=True)
    except (json.JSONDecodeError, KeyError) as e:
        print_2b_message(f"Tive um problema para decidir a ação. Vamos tratar como um chat. Detalhe: {e}", is_warning=True)
        add_history_entry("user", user_query_string)
        chat_command(MockArgs(query=user_query_string.split()), start_interactive_after_reply=True)


# --- Parser de Argumentos ---
def main():
    """Função principal que lida com os argumentos da linha de comando e despacha para as funções corretas."""
    # --- Guardião de Segurança e Autocura ---
    # Este bloco é executado no início de cada comando.
    # Ele verifica se a chave da API está salva de forma insegura e tenta migrá-la para o keyring.
    # Não executa se o usuário já estiver tentando rodar o 'config'.
    if 'config' not in sys.argv:
        try:
            config = load_config()
            # A condição de cura: keyring está instalado E uma chave insegura ainda existe.
            if KEYRING_AVAILABLE and config.get('api_key'):
                insecure_key = config.get('api_key')
                
                print_2b_message(
                    "Detectei uma chave de API insegura e o 'keyring' já está disponível. "
                    "Movendo para o seu keychain seguro agora...",
                    is_info=True,
                    skip_panel=True
                )
                
                # Faz a migração diretamente aqui.
                if save_api_key_securely(insecure_key):
                    # Se a chave foi salva com sucesso no keychain...
                    # removemos do dicionário de configuração...
                    config.pop('api_key')
                    # ...e salvamos o arquivo de configuração modificado no disco.
                    save_config(config)
                    
                    print_2b_message("Prontinho! Sua chave agora está protegida no keychain. ✨", is_success=True)
                else:
                    # Se a migração falhar, avisamos mas não mudamos nada.
                    print_2b_message("Não consegui mover a chave para o keychain. Ela permanecerá insegura por enquanto.", is_warning=True)

        except Exception:
            pass # Ignora erros durante a autocura para não travar o programa.
            
    parser = argparse.ArgumentParser(
        description="2B: Sua assistente de IA pessoal no terminal. 🖤🤖\nUse '2b <comando> --help' para mais detalhes.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""Exemplos:
  2b do "liste os processos na porta 8080"
  2b search "melhor editor de texto para python"
  2b "lembre-me de comprar pão amanhã às 10h"
"""
    )
    VERSION = "2ByNekyl-1.1.1" # Versão do programa.
    parser.add_argument('--version', '-v', action='store_true', help='Mostra a versão do programa')
    subparsers = parser.add_subparsers(dest="command", help="Comandos da 2B") # Define os subcomandos.
    
    # Configuração do subcomando 'do'.
    do_parser = subparsers.add_parser("do", aliases=['d'], help="Executa tarefas no terminal de forma sequencial e interativa.")
    do_parser.add_argument("query", nargs="+", type=str, help="A tarefa que você quer que a 2B execute.")
    do_parser.add_argument("--timeout", type=int, default=300, help="Timeout para cada passo (padrão: 300s).")
    do_parser.add_argument("--max-steps", type=int, default=20, help="Número máximo de passos que o agente pode executar (padrão: 20).")
    do_parser.set_defaults(func=do_command)
    
    # Configuração do subcomando 'search'.
    search_parser = subparsers.add_parser("search", aliases=['s'], help="Busca um tópico na web e resume os resultados.")
    search_parser.add_argument("query", nargs="+", type=str, help="O que você quer pesquisar?")
    search_parser.add_argument('--debug', action='store_true', help='Salva o HTML da busca para depuração.')
    search_parser.set_defaults(func=search_command)
    
    # Configuração do subcomando 'explain'.
    explain_parser = subparsers.add_parser("explain", aliases=['ex'], help="Explica um comando, erro ou conteúdo de arquivo.")
    explain_parser.add_argument("query", nargs="?", type=str, help="O comando, erro ou pergunta sobre o arquivo.")
    explain_parser.add_argument("--from-file", "-f", type=str, help="Caminho do arquivo para explicar.")
    explain_parser.set_defaults(func=explain_command)
    
    # Configuração do subcomando 'generate'.
    generate_parser = subparsers.add_parser("generate", aliases=['gen'], help="Gera código, scripts ou configurações.")
    generate_parser.add_argument("query", type=str, help="Descrição do que gerar.")
    generate_parser.add_argument("--lang", "-l", type=str, help="Linguagem/tipo (ex: python, bash).")
    generate_parser.add_argument("--output", "-o", type=str, help="Arquivo para salvar o código gerado.")
    generate_parser.add_argument("--input-file", "-i", dest="input_file_path", type=str, help="Arquivo de entrada para contexto.")
    generate_parser.set_defaults(func=generate_command)
    
    # Configuração do subcomando 'chat'.
    chat_parser = subparsers.add_parser("chat", aliases=['c'], help="Chat interativo ou pergunta direta.")
    chat_parser.add_argument("query", nargs="*", type=str, help="Pergunta (opcional para chat interativo).")
    chat_parser.set_defaults(func=chat_command)
    
    # Configuração do subcomando 'greet'.
    greet_parser = subparsers.add_parser("greet", aliases=['hi'], help="Saudação da 2B (ótimo para .bashrc/.zshrc).")
    greet_parser.set_defaults(func=greet_command)
    
    # Configuração do subcomando 'remember' e seus sub-subcomandos.
    remember_parser = subparsers.add_parser("remember", aliases=['rem'], help="Gerencia lembretes.")
    rem_subs = remember_parser.add_subparsers(dest="remember_action", help="Ação para o lembrete", required=True)
    rem_add = rem_subs.add_parser("add", help="Adiciona lembrete."); rem_add.add_argument("text", type=str, help="Texto do lembrete."); rem_add.set_defaults(func=remember_add)
    rem_list = rem_subs.add_parser("ls", help="Lista lembretes."); rem_list.add_argument("--all", action="store_true", help="Inclui concluídos."); rem_list.set_defaults(func=remember_list)
    rem_done = rem_subs.add_parser("done", help="Marca lembrete como concluído."); rem_done.add_argument("id", type=str, help="ID do lembrete."); rem_done.set_defaults(func=remember_done)
    rem_clear = rem_subs.add_parser("rm", help="Apaga lembretes."); rem_clear.add_argument("id", type=str, help="ID, 'all' (todos), ou 'done' (concluídos)."); rem_clear.set_defaults(func=remember_clear)
    
    # Configuração do subcomando 'config'.
    config_parser = subparsers.add_parser("config", help="Configura a 2B (API Key, personalidade, user).")
    config_parser.add_argument("key", nargs="?", type=str, help="Chave da configuração (api_key, personality, user).")
    config_parser.add_argument("value", nargs="?", type=str, help="Valor para a configuração.")
    config_parser.set_defaults(func=config_command)
    
    known_commands = list(subparsers.choices.keys())
    safe_flags = ['--version', '-v']
    # Se o primeiro argumento não for um comando conhecido, assume que é uma query para o dispatcher.
    if len(sys.argv) > 1 and sys.argv[1] not in known_commands and sys.argv[1] not in safe_flags:
        user_query_string = " ".join(sys.argv[1:])
        dispatcher_command(user_query_string) # Chama o dispatcher para decidir o que fazer.
        return

    args = parser.parse_args() # Faz o parse dos argumentos da linha de comando.
    if args.version:
        # Mostra a versão e o status das dependências.
        if RICH_AVAILABLE:
            from rich import print
            bs_status = "[green]OK[/green]" if BS4_AVAILABLE else "[red]Faltando[/red]"
            lxml_status = "[green]OK[/green]" if LXML_AVAILABLE else "[yellow]Opcional (não instalada)[/yellow]"
            print(f"[bold hot_pink3]{parser.prog}[/bold hot_pink3] [green]{VERSION}[/green]")
            print(Text.from_markup(f"[dim]Dependências de busca: BeautifulSoup4 ({bs_status}), lxml ({lxml_status})[/dim]"))
        else:
            print(f"{parser.prog} {VERSION}")
        return
    if hasattr(args, 'func'):
        try:
            args.func(args) # Chama a função associada ao subcomando.
        except Exception as e:
            print_2b_message(f"Oh não, um erro inesperado aconteceu: {e}\nPor favor, reporte isso para que eu possa melhorar!", is_error=True)
            if RICH_AVAILABLE:
                from rich.traceback import Traceback
                CONSOLE.print(Traceback(show_locals=False)) # Mostra o traceback se o Rich estiver disponível.
    else:
        greet_command(args) # Se nenhum comando for especificado, mostra a saudação.

if __name__ == "__main__":
    # Se o programa for executado sem argumentos, ele chama o comando 'greet' por padrão.
    if len(sys.argv) == 1:
        sys.argv.append('greet')
    main() # Inicia a função principal.
