import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import threading
import time
import os
import queue
import re
import json
import subprocess
import shlex
from datetime import datetime
from collections import deque
import sys
from PIL import Image # Importante para CustomTkinter/PyAutoGUI

# --- Importações para novas funcionalidades ---
SCREENSHOT_DISPONIVEL = False
try:
    import pyautogui
    SCREENSHOT_DISPONIVEL = True
except ImportError:
    pass

OLLAMA_DISPONIVEL = False
try:
    import ollama
    OLLAMA_DISPONIVEL = True
except ImportError:
    pass

# ==============================================================================
# CONFIGURAÇÕES GLOBAIS
# ==============================================================================
APP_VERSION = "24.0 (Layout Otimizado PT-BR)" # Versão atualizada
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
CORNER_RADIUS = 6
# Ajustes finos de padding para melhor aproveitamento do espaço
PADX_MAIN_CONTENT = 8 
PADY_MAIN_CONTENT = 6


CONFIG_FILE = "monitor_config.json"
HISTORY_DIR = "log_history"
EVIDENCE_DIR = "error_evidence"

# ==============================================================================
# BASE DE CONHECIMENTO E ANÁLISE APRIMORADA
# ==============================================================================
BASE_DE_CONHECIMENTO_ERROS = {
    # Erros de Autenticação/Credenciais
    r'Falha na autenticação\. Motivo: Usuário ou Senha inválidos': {'categoria': "Erro de Autenticação", 'status_tag': "ERRO CRÍTICO", 'sugestao': "Verifique as credenciais e a disponibilidade do serviço de autenticação."},
    
    # Erros de Rede/Conexão (captura código HTTP)
    r'org\.apache\.commons\.httpclient\.HttpException: (\d{3})': {'categoria': "Recurso Não Encontrado (HTTP \\1)", 'status_tag': "ERRO MAPEADO", 'sugestao': "URL inválida ou recurso indisponível. Verifique o endereço e a disponibilidade do serviço. Código: \\1."},
    r'Connection timed out: connect': {'categoria': "Timeout de Conexão de Rede", 'status_tag': "ERRO CRÍTICO", 'sugestao': "O servidor remoto não respondeu a tempo. Verifique a conectividade de rede, firewall e disponibilidade do serviço remoto."},
    r'java\.net\.ConnectException': {'categoria': "Falha na Conexão de Rede", 'status_tag': "ERRO CRÍTICO", 'sugestao': "Problema ao estabelecer conexão com o servidor remoto. Verifique a rede, IP/porta do servidor e firewall."},
    r'Falha ao obter imagem do Banner Ofertas Inteligentes': {'categoria': "Erro: Carga de Imagem/Banner Falhou", 'status_tag': "ERRO MAPEADO", 'sugestao': "O aplicativo não conseguiu carregar uma imagem externa (banner). Verifique a URL do banner e a conectividade com o servidor de mídias."},
    r'Não foi possível obter o arquivo de retorno \[.+?\] pelo integrador \[.+?\]': {'categoria': "Erro: Falha na Recuperação de Retorno", 'status_tag': "ERRO CRÍTICO", 'sugestao': "O sistema não conseguiu baixar um arquivo de retorno de um integrador. Pode ser problema de rede, permissão ou o arquivo não está disponível no servidor remoto."},

    # Erros de Lógica/Programação (Java)
    r'java\.lang\.NullPointerException: (.*)': {'categoria': "Erro de Referência Nula (NPE)", 'status_tag': "ERRO CRÍTICO", 'sugestao': "Uma variável estava 'nula' quando o código tentou usá-la. Detalhes: \\1. Isso é um erro de programação, requer análise do stack trace. Pode indicar dados faltando ou lógica incorreta."},
    r'Falha ao calcular caixa padrão para o produto \[(\d+?) - (.+?)\]\.': {'categoria': "Erro de Cálculo de Regra de Negócio", 'status_tag': "ERRO MAPEADO", 'sugestao': "Falha ao calcular regra para o produto ID \\1 (\\2). Analise o stack trace e os dados do produto envolvido. Pode ser dados inválidos ou regra mal definida."},
    r'Tentou carregar dados de um produto \[nulo\] na grid de pedidos': {'categoria': "Dados Nulos na Interface/Backend", 'status_tag': "ERRO MAPEADO", 'sugestao': "A interface tentou exibir um produto 'nulo' ou dados incompletos. A falha ocorreu na camada de busca de dados ou na preparação do objeto. Verifique a integridade dos dados."},
    r'Não foi possível finalizar a execução': {'categoria': "Aviso: Execução Não Finalizada", 'status_tag': "AVISO MAPEADO", 'sugestao': "Uma tarefa ou thread não conseguiu concluir sua execução normalmente. Isso pode indicar um deadlock, um loop infinito ou um erro não tratado. Analise o stack trace para mais detalhes."},

    # Avisos e Falhas de Ambiente/Configuração
    r'GRAVE: Falha ao carregar configurações de proxy\.': {'categoria': "Erro Grave: Configuração de Proxy", 'status_tag': "ERRO CRÍTICO", 'sugestao': "O aplicativo não conseguiu carregar as configurações de proxy. Verifique as configurações de rede do sistema e do aplicativo. Isso pode impedir o acesso à internet."},
    r'dir not exists': {'categoria': "Aviso: Diretório de Ambiente Ausente", 'status_tag': "AVISO MAPEADO", 'sugestao': "Um diretório esperado para a operação não existe. Verifique o caminho configurado e as permissões de acesso da aplicação."},
    r'Timeout para visualização do loading excedido': {'categoria': "Aviso: Timeout de Operação de Interface", 'status_tag': "AVISO MAPEADO", 'sugestao': "Uma tarefa demorou mais que o tempo limite de exibição. Pode indicar lentidão geral do sistema, gargalo de I/O ou processamento demorado."},
    r'\[NOT FOUND\]': {'categoria': "Aviso: Dependência/Recurso Interno Faltando", 'status_tag': "AVISO MAPEADO", 'sugestao': "O 'Health Check' ou verificação interna detectou que arquivos .jar esperados ou dependências não foram encontrados. Pode causar falhas futuras."},
    r'outOfOrder mode is active': {'categoria': "Aviso: Migração de Banco (Flyway Fora de Ordem)", 'status_tag': "AVISO MAPEADO", 'sugestao': "Aviso do Flyway: migrações de BD fora de ordem. O schema pode não ser reprodutível ou causar inconsistências. Verifique o histórico de migrações e a versão do BD."},
    r'Ocorreu um erro ao obter o banner OFI\.': {'categoria': "Aviso: Falha na Carga de Banner", 'status_tag': "AVISO MAPEADO", 'sugestao': "Um erro ocorreu ao tentar carregar o banner de ofertas inteligentes. O erro pode ser detalhado em outra linha. Verifique a fonte do banner e a URL."},
    r'slf4j LogbackLogger binder not found, no logger will be available\.': {'categoria': "Aviso: Configuração de Log Faltando", 'status_tag': "AVISO MAPEADO", 'sugestao': "O binder para o Logback (biblioteca de log) não foi encontrado. Isso significa que a aplicação pode não estar gerando logs detalhados, dificultando a depuração."},
    r'CAMPO (.+?) N\\u00C3O DEFINIDO NO ARQUIVO \.conf': {'categoria': "Aviso: Parâmetro de Configuração Ausente", 'status_tag': "AVISO MAPEADO", 'sugestao': "O parâmetro de configuração '\\1' não foi definido em .conf. A aplicação pode estar usando um valor padrão ou ter um comportamento inesperado."},
    r'Current TZ: GMT-03:00\s+If the current timezone is not Sao Paulo \(or any other\s+TZ GMT-3\) the application is not properly configured': {'categoria': "Aviso: Configuração de Fuso Horário Incorreta", 'status_tag': "AVISO MAPEADO", 'sugestao': "O fuso horário do sistema pode não estar configurado corretamente para o aplicativo, o que pode causar inconsistências em registros de data/hora ou operações sensíveis a fuso horário. Ajuste a variável de ambiente 'user.timezone'."},
    r'Levou (\d+) milis para calcular ST para (\d+) registros para o cliente (\d+)\.': {'categoria': "Performance: Cálculo de ST (tempo: \\1ms)", 'status_tag': "INFO DE PERFORMANCE", 'sugestao': "O cálculo de Substituição Tributária levou \\1ms para \\2 registros do cliente \\3. Monitore se este tempo aumenta, pois pode indicar gargalos de performance."},
    r'Levou (\d+) milis para carregar os dados do (.+?)\.\.\.': {'categoria': "Performance: Carga de Dados (tempo: \\1ms)", 'status_tag': "INFO DE PERFORMANCE", 'sugestao': "A operação de carga de dados para '\\2' levou \\1ms. Monitore este tempo para identificar lentidão no acesso a dados ou processamento inicial."},
    r'Conectado em (.+?)': {'categoria': "INFO: Conexão de Rede Estabelecida", 'status_tag': "INFO", 'sugestao': "Conexão de rede estabelecida com sucesso ao host: \\1."},
    r'Autenticado em (.+?)': {'categoria': "INFO: Autenticação Bem-Sucedida", 'status_tag': "INFO", 'sugestao': "Autenticação bem-sucedida para o usuário/serviço: \\1."},
    r'Arquivo \[.+?\] enviado com sucesso para faturamento pelo integrador \[.+?\]\.': {'categoria': "INFO: Envio de Arquivo Bem-Sucedido", 'status_tag': "INFO", 'sugestao': "Um arquivo foi enviado com sucesso para o faturamento. Confirme o processamento no sistema de destino."},
    r'Resposta do Middleware Grupo para o registro de pedidos: \{"message":"Pedidos registrados com sucesso\."\}': {'categoria': "INFO: Pedido Registrado com Sucesso", 'status_tag': "SUCESSO", 'sugestao': "O pedido foi registrado com sucesso no Middleware do Grupo. Verifique o status final do pedido."},

}

def analisar_bloco_com_ia(bloco_de_texto, ia_enabled=True, ollama_model='llama31-8b-f32:latest'):
    bloco_lower = bloco_de_texto.lower()
    
    detected_log_level_for_ia = "LOG"
    if re.search(r'\[ERROR\]|GRAVE:', bloco_de_texto):
        detected_log_level_for_ia = "ERRO"
    elif re.search(r'\[WARN\]|AVISO:', bloco_de_texto):
        detected_log_level_for_ia = "AVISO"
    elif re.search(r'\[INFO\]|INFORMAÇÕES:', bloco_de_texto):
        detected_log_level_for_ia = "INFO"

    # --- 1. Tentar Mapeamento por Padrão (Base de Conhecimento) ---
    for padrao, info in BASE_DE_CONHECIMENTO_ERROS.items():
        match = re.search(padrao, bloco_de_texto, re.IGNORECASE)
        if match:
            categoria = info['categoria']
            sugestao = info['sugestao']
            if match.groups():
                for i, group_val in enumerate(match.groups()):
                    categoria = categoria.replace(f"\\{i+1}", group_val)
                    sugestao = sugestao.replace(f"\\{i+1}", group_val)

            # Se um padrão é mapeado, SEMPRE retorna o resultado.
            # Este é o comportamento desejado para análise rápida local.
            return {
                "status": info.get('status_tag', "MAPEADO"),
                "resumo": categoria,
                "sugestao": sugestao,
                "causa_raiz": "N/A", 
                "componente_afetado": "N/A",
                "id_entidade": "N/A",
                "tempo_execucao_ms": "N/A",
            }
    
    # --- 2. Se nenhum padrão foi mapeado, verificamos a opção da IA ---
    if not ia_enabled:
        # Se IA desabilitada E NENHUM PADRÃO FOI MAPEADO, não há necessidade de análise por IA.
        # Retorna None para que NENHUM bloco de análise seja exibido para este caso.
        return None 
    
    # --- 3. Se IA habilitada, mas Ollama indisponível, exibir aviso de indisponibilidade ---
    if not OLLAMA_DISPONIVEL:
        # Isso ainda é considerado um bloco de análise, pois a IA foi "pedida" mas não pôde ser usada.
        return {"status": "OLLAMA_INDISPONIVEL", "resumo": "Ollama não detectado.", "sugestao": "Instale a biblioteca 'ollama' e garanta que o servidor Ollama esteja em execução e o modelo carregado para análise por IA.", "causa_raiz": "Ollama não acessível", "componente_afetado": "Sistema/Ollama", "id_entidade": "N/A", "tempo_execucao_ms": "N/A"}

    # --- 4. Chamar a IA (Ollama) para análise profunda (só se ia_enabled e Ollama_DISPONIVEL) ---
    prompt = f"""Você é um engenheiro SRE altamente experiente e um analista de logs Java. Sua principal tarefa é identificar a causa raiz de problemas e fornecer soluções acionáveis.

    Analise o seguinte bloco de {detected_log_level_for_ia} do log. Seu foco deve ser em:
    - **Identificar o problema principal:** É um erro, aviso, ou um evento informativo de performance/configuração?
    - **Determinar a causa raiz:** O que provavelmente causou o evento?
    - **Sugerir uma ação:** O que deve ser verificado ou feito para resolver/investigar?
    - **Extrair detalhes:** Quaisquer IDs, nomes de produtos, URLs, classes Java, ou tempos de execução.

    Sua resposta deve ser APENAS um objeto JSON válido com as seguintes chaves, mesmo que um valor não seja aplicável (use "N/A"):
    - "status": Uma palavra-chave clara: "ERRO", "AVISO", "INFO" ou "SUCESSO". (O status deve refletir a gravidade do problema, não apenas o nível de log).
    - "resumo": Uma frase concisa (até 15 palavras) que descreva o problema ou evento principal.
    - "sugestao": Uma ou duas frases (até 30 palavras) com uma ação ou investigação recomendada.
    - "causa_raiz": A causa raiz mais provável do problema, se identificável.
    - "componente_afetado": O nome da classe ou módulo Java que parece estar com o problema principal.
    - "id_entidade": Qualquer ID de produto, cliente, transação, etc., se presente no log.
    - "tempo_execucao_ms": Se o log indicar um tempo de execução para uma operação, extraia-o em milissegundos.

    **Exemplo de Resposta JSON:**
    ```json
    {{
        "status": "ERRO",
        "resumo": "Falha na conexão com o banco de dados.",
        "sugestao": "Verifique as credenciais do banco e a conectividade de rede.",
        "causa_raiz": "Configuração de driver JDBC incorreta.",
        "componente_afetado": "org.hibernate.c3p0",
        "id_entidade": "N/A",
        "tempo_execucao_ms": "N/A"
    }}
    ```

    **Log a ser analisado:**
    ```
    {bloco_de_texto}
    ```
    """
    try:
        response = ollama.chat(model=ollama_model, messages=[{'role': 'user', 'content': prompt}], format='json', stream=False)
        resultado_dict = json.loads(response['message']['content'])
        
        for key in ["causa_raiz", "componente_afetado", "id_entidade", "tempo_execucao_ms"]:
            resultado_dict.setdefault(key, "N/A")

        if not all(k in resultado_dict for k in ["status", "resumo", "sugestao"]):
            return {"status": "ERRO_IA_FORMATO", "resumo": "A IA retornou um JSON com formato inesperado.", "sugestao": f"Resposta RAW: {response['message']['content'][:200]}...", "causa_raiz": "N/A", "componente_afetado": "N/A", "id_entidade": "N/A", "tempo_execucao_ms": "N/A"}
            
        ia_status = resultado_dict.get("status", "ANALISADO").upper()
        if "ERRO" in ia_status:
            resultado_dict["status"] = "ERRO_IA"
        elif "AVISO" in ia_status or "WARN" in ia_status:
            resultado_dict["status"] = "AVISO_IA"
        else:
            resultado_dict["status"] = "INFO_IA"
            
        return resultado_dict
        
    except json.JSONDecodeError:
        return {"status": "ERRO_IA_JSON", "resumo": "A IA retornou uma resposta em formato JSON inválido.", "sugestao": f"Resposta RAW: {response['message']['content'][:200]}...", "causa_raiz": "N/A", "componente_afetado": "N/A", "id_entidade": "N/A", "tempo_execucao_ms": "N/A"}
    except Exception as e:
        return {"status": "ERRO_OLLAMA", "resumo": f"Falha ao comunicar com o Ollama: {e}", "sugestao": "Verifique se o servidor Ollama está em execução e se o modelo está carregado corretamente.", "causa_raiz": "Problema de comunicação com LLM", "componente_afetado": "Ollama/Rede", "id_entidade": "N/A", "tempo_execucao_ms": "N/A"}


class ModernAppTemplate(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Nome do Seu Aplicativo")
        # Ajuste a geometria inicial para ser um pouco maior, mas ainda responsiva
        self.geometry("1200x750") 
        ctk.set_appearance_mode("dark")
        self.configure(fg_color="#2B2B2B")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.nav_buttons = {}
        self.content_frames = {}
        
        self.NAV_ITEMS = {
            "monitor": ("🖥️", "Monitor"),
            "settings": ("⚙️", "Configurações"),
            "history": ("📜", "Histórico")
        }

        self._create_navigation_frame()
        self._create_content_frames()


    def _create_navigation_frame(self):
        """Cria a barra de navegação lateral. Esta parte é reutilizável."""
        nav_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#202020")
        nav_frame.grid(row=0, column=0, sticky="nsw")
        nav_frame.grid_rowconfigure(len(self.NAV_ITEMS) + 2, weight=1)

        logo_label = ctk.CTkLabel(nav_frame, text="SRE Monitor",
                                   font=ctk.CTkFont(size=22, weight="bold"))
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 20))

        for i, (name, (icon, text)) in enumerate(self.NAV_ITEMS.items(), start=1):
            button = ctk.CTkButton(nav_frame, text=f"  {icon}    {text}",
                                   height=35,
                                   corner_radius=8,
                                   fg_color="transparent",
                                   text_color="#A0A0A0",
                                   hover_color="#333333",
                                   anchor="w",
                                   font=ctk.CTkFont(size=14),
                                   command=lambda n=name: self.select_frame_by_name(n))
            button.grid(row=i, column=0, padx=10, pady=4, sticky="ew")
            self.nav_buttons[name] = button

    def _create_content_frames(self):
        """Cria o container principal e os frames vazios para cada página."""
        self.content_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=PADX_MAIN_CONTENT, pady=PADY_MAIN_CONTENT)

        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(0, weight=1)

        for name in self.NAV_ITEMS:
            frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
            frame.grid(row=0, column=0, sticky="nsew")
            self.content_frames[name] = frame

    def select_frame_by_name(self, name):
        """Lógica para mostrar uma página e destacar o botão correspondente."""
        for btn_name, button in self.nav_buttons.items():
            button.configure(fg_color="transparent", text_color="#A0A0A0")

        selected_button = self.nav_buttons.get(name)
        if selected_button:
            selected_button.configure(fg_color="#007AFF", text_color="white")

        frame_to_show = self.content_frames.get(name)
        if frame_to_show:
            frame_to_show.tkraise()
            # Se for a página de histórico, atualiza a lista de arquivos
            if name == "history":
                self.populate_history_listbox()


    def _create_toolbar(self, parent_frame, title):
        """Função utilitária para criar uma barra de ferramentas padrão para cada página."""
        toolbar_frame = ctk.CTkFrame(parent_frame, fg_color="transparent", height=50)
        
        title_label = ctk.CTkLabel(toolbar_frame, text=title,
                                   font=ctk.CTkFont(size=28, weight="bold"))
        title_label.pack(side="left", padx=5, pady=10)
        
        return toolbar_frame

    def setup_monitor_page(self, parent_frame): pass
    def setup_settings_page(self, parent_frame): pass
    def setup_history_page(self, parent_frame): pass

class LogMonitorAppModern(ModernAppTemplate):
    def __init__(self):
        super().__init__()

        self.command_var = tk.StringVar()
        self.command_var.trace_add('write', self._schedule_auto_save) 

        self.workdir_var = tk.StringVar()
        self.workdir_var.trace_add('write', self._schedule_auto_save) 

        self.keywords_var = tk.StringVar()
        self.keywords_var.trace_add('write', self._schedule_auto_save) 

        self.ia_enabled_var = tk.BooleanVar(value=True)
        self.ia_enabled_var.trace_add('write', self._schedule_auto_save) 

        self.ollama_model_var = tk.StringVar(value='llama31-8b-f32:latest') # Nova variável para o modelo Ollama
        self.ollama_model_var.trace_add('write', self._schedule_auto_save)

        self.log_encoding_var = tk.StringVar(value='latin-1') # Nova variável para encoding do log
        self.log_encoding_var.trace_add('write', self._schedule_auto_save)

        self.max_log_lines_var = tk.IntVar(value=3000)
        self.max_log_lines_var.trace_add('write', self._schedule_auto_save) 

        self.capture_evidence_var = tk.BooleanVar(value=True)
        self.capture_evidence_var.trace_add('write', self._schedule_auto_save) 
        
        self.search_term_monitor = tk.StringVar()
        self.search_term_history = tk.StringVar()
        
        self.auto_save_job = None 

        self.is_monitoring = False
        self.process_thread = None
        self.java_process = None
        self.log_queue = queue.Queue()
        self.current_session_filepath = None
        self.last_search_pos_monitor = "1.0"
        self.last_searched_term_monitor = ""
        self.last_search_pos_history = "1.0"
        self.last_searched_term_history = ""
        
        self.log_buffer = []
        self.analysis_lock = threading.Lock()
        self.user_actions = deque(maxlen=20)

        self.analysis_results_summary_buffer = [] 
        self.detected_connections = set()

        self.title(f"Monitor de Processos com IA v{APP_VERSION}")

        os.makedirs(HISTORY_DIR, exist_ok=True)
        os.makedirs(EVIDENCE_DIR, exist_ok=True)
        
        self.setup_monitor_page(self.content_frames["monitor"])
        self.setup_settings_page(self.content_frames["settings"])
        self.setup_history_page(self.content_frames["history"])

        first_page_name = next(iter(self.NAV_ITEMS))
        self.select_frame_by_name(first_page_name)

        self.load_config()
        self.after(250, self.process_log_queue)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log_action("Aplicação iniciada.")

    def _schedule_auto_save(self, *args):
        """Agenda o salvamento automático com um pequeno atraso para evitar múltiplas chamadas."""
        if self.auto_save_job:
            self.after_cancel(self.auto_save_job)
        self.auto_save_job = self.after(1000, self.save_config)

    def log_action(self, action_description):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.user_actions.append(f"[{timestamp}] {action_description}")

    def capture_evidence(self):
        if not self.capture_evidence_var.get():
            return

        if not SCREENSHOT_DISPONIVEL:
            self.log_action("AVISO: Tentativa de captura de evidência falhou. 'pyautogui' não está instalado.")
            return

        try:
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            base_filename = os.path.join(EVIDENCE_DIR, f"evidencia_{timestamp}")
            screenshot_filename = f"{base_filename}.png"
            actions_filename = f"{base_filename}_acoes.txt"

            pyautogui.screenshot(screenshot_filename)
            self.log_action(f"Screenshot salvo em: {screenshot_filename}")

            with open(actions_filename, 'w', encoding='utf-8') as f:
                f.write("--- Últimas Ações do Usuário ---\n\n")
                for action in self.user_actions:
                    f.write(f"{action}\n")
            self.log_action(f"Log de ações salvo em: {actions_filename}")

        except Exception as e:
            self.log_action(f"ERRO ao capturar evidência: {e}")
            messagebox.showerror("Erro de Evidência", f"Não foi possível capturar a evidência.\nErro: {e}\n\nVerifique as permissões ou se o Pillow está instalado corretamente.")


    def setup_monitor_page(self, parent_frame):
        """Cria a interface da página 'Monitor' (Layout Melhorado)."""
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_frame.grid_rowconfigure(1, weight=1) # Log textbox expande em altura

        toolbar = ctk.CTkFrame(parent_frame, fg_color="transparent", height=50)
        toolbar.grid(row=0, column=0, padx=PADX_MAIN_CONTENT, pady=(0, PADY_MAIN_CONTENT), sticky="ew")
        toolbar.grid_columnconfigure(0, weight=1) # Espaço para o título
        toolbar.grid_columnconfigure(1, weight=0) # Agrupa os botões à direita

        title_label = ctk.CTkLabel(toolbar, text="Monitor de Processos",
                                   font=ctk.CTkFont(size=28, weight="bold"))
        title_label.grid(row=0, column=0, padx=5, pady=10, sticky="w")

        controls_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        controls_frame.grid(row=0, column=1, padx=0, pady=0, sticky="e")
        
        # Otimizando as colunas dentro do controls_frame
        controls_frame.grid_columnconfigure(0, weight=1) # Coluna para a busca (expande)
        controls_frame.grid_columnconfigure(1, weight=0) # Botão busca
        controls_frame.grid_columnconfigure(2, weight=0) # Botão Iniciar
        controls_frame.grid_columnconfigure(3, weight=0) # Botão Parar
        controls_frame.grid_columnconfigure(4, weight=0) # Botão Exportar
        controls_frame.grid_columnconfigure(5, weight=0) # Botão Limpar Ações


        # Linha 0: Campo de Busca + Botão Lupa + Botões de Ação
        self.search_entry_monitor = ctk.CTkEntry(controls_frame, textvariable=self.search_term_monitor, placeholder_text="Buscar no log...", corner_radius=CORNER_RADIUS, width=180) # Largura ajustada
        self.search_entry_monitor.grid(row=0, column=0, padx=(0, 2), pady=10, sticky="ew") # Preenche horizontalmente
        self.search_entry_monitor.bind("<Return>", lambda e: self.search_in_monitor())
        
        self.search_button_monitor = ctk.CTkButton(controls_frame, text="🔎", command=self.search_in_monitor, width=35, corner_radius=CORNER_RADIUS) # Largura ajustada
        self.search_button_monitor.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="w")

        # Botões de Ação (agrupados mais à direita)
        self.start_button = ctk.CTkButton(controls_frame, text="▶ Iniciar", command=lambda: [self.log_action("Botão 'Iniciar Análise' clicado."), self.start_monitoring()], corner_radius=CORNER_RADIUS, width=80)
        self.start_button.grid(row=0, column=2, padx=(0, 5), pady=10, sticky="e") 
        
        self.stop_button = ctk.CTkButton(controls_frame, text="■ Parar", command=lambda: [self.log_action("Botão 'Parar Análise' clicado."), self.stop_monitoring()], state='disabled', corner_radius=CORNER_RADIUS, fg_color="#D32F2F", hover_color="#B71C1C", width=80)
        self.stop_button.grid(row=0, column=3, padx=(0, 5), pady=10, sticky="e")

        self.export_button_monitor = ctk.CTkButton(controls_frame, text="Exportar", command=lambda: [self.log_action("Botão 'Exportar Log' (Monitor) clicado."), self.export_monitor_log()], corner_radius=CORNER_RADIUS, width=80)
        self.export_button_monitor.grid(row=0, column=4, padx=(0, 5), pady=10, sticky="e")

        self.clear_actions_button = ctk.CTkButton(controls_frame, text="Limpar Ações", command=lambda: [self.log_action("Botão 'Limpar Ações' clicado."), self.user_actions.clear(), messagebox.showinfo("Limpar Ações", "Histórico de ações do usuário limpo.")], corner_radius=CORNER_RADIUS, width=100)
        self.clear_actions_button.grid(row=0, column=5, padx=(0, 0), pady=10, sticky="e") # Último à direita

        # Área de Log Principal
        self.log_textbox = ctk.CTkTextbox(parent_frame, wrap=tk.WORD, font=("Consolas", 11), corner_radius=CORNER_RADIUS, border_width=1, fg_color="#333333")
        self.log_textbox.grid(row=1, column=0, padx=PADX_MAIN_CONTENT, pady=(0, PADY_MAIN_CONTENT), sticky="nsew")
        self.log_textbox.configure(state=tk.DISABLED)
        self.log_textbox.tag_config("aviso", foreground="#FFD700")
        self.log_textbox.tag_config("erro", foreground="#FF5252")
        self.log_textbox.tag_config("info", foreground="#40C4FF")
        self.log_textbox.tag_config("titulo", foreground="#FFFFFF", justify="center") 
        self.log_textbox.tag_config("search_highlight", background="#F9A825", foreground="black")
        
        # Correção final para o erro de fonte no tag_config (removendo a opção 'font')
        self.log_textbox.tag_config("summary_header", foreground="#8ECDEC") 


    def setup_settings_page(self, parent_frame):
        """Cria a interface da página 'Configurações'."""
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_frame.grid_rowconfigure(0, weight=0)
        parent_frame.grid_rowconfigure(1, weight=1)

        toolbar = self._create_toolbar(parent_frame, "Configurações")
        toolbar.grid(row=0, column=0, padx=PADX_MAIN_CONTENT, pady=(0, PADY_MAIN_CONTENT), sticky="ew")
        
        scrollable_content = ctk.CTkScrollableFrame(parent_frame, fg_color="transparent")
        scrollable_content.grid(row=1, column=0, padx=PADX_MAIN_CONTENT, pady=(0, PADY_MAIN_CONTENT), sticky="nsew")
        scrollable_content.grid_columnconfigure(1, weight=1)

        app_config_frame = ctk.CTkFrame(scrollable_content, fg_color="transparent")
        app_config_frame.pack(fill="x", padx=20, pady=(15, 10))
        app_config_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(app_config_frame, text="### Configurações da Aplicação a Monitorar", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, padx=PADX_MAIN_CONTENT, pady=(0, 10), sticky="w")
        
        ctk.CTkLabel(app_config_frame, text="Aplicação (.jar ou .exe):").grid(row=1, column=0, padx=PADX_MAIN_CONTENT, pady=(PADY_MAIN_CONTENT*2, PADY_MAIN_CONTENT), sticky="w")
        self.browse_button = ctk.CTkButton(app_config_frame, text="Procurar Executável...", command=self.escolher_executavel, corner_radius=CORNER_RADIUS)
        self.browse_button.grid(row=1, column=1, padx=PADX_MAIN_CONTENT, pady=(PADY_MAIN_CONTENT*2, PADY_MAIN_CONTENT), sticky="w")
        
        ctk.CTkLabel(app_config_frame, text="Comando de Execução:").grid(row=2, column=0, padx=PADX_MAIN_CONTENT, pady=PADY_MAIN_CONTENT, sticky="w")
        self.entry_command = ctk.CTkEntry(app_config_frame, textvariable=self.command_var, corner_radius=CORNER_RADIUS)
        self.entry_command.grid(row=2, column=1, padx=PADX_MAIN_CONTENT, pady=PADY_MAIN_CONTENT, sticky="ew")
        
        ctk.CTkLabel(app_config_frame, text="Diretório de Trabalho:").grid(row=3, column=0, padx=PADX_MAIN_CONTENT, pady=PADY_MAIN_CONTENT, sticky="w")
        self.entry_workdir = ctk.CTkEntry(app_config_frame, textvariable=self.workdir_var, corner_radius=CORNER_RADIUS)
        self.entry_workdir.grid(row=3, column=1, padx=PADX_MAIN_CONTENT, pady=PADY_MAIN_CONTENT, sticky="ew")

        ctk.CTkLabel(app_config_frame, text="Encoding do Log:").grid(row=4, column=0, padx=PADX_MAIN_CONTENT, pady=PADY_MAIN_CONTENT, sticky="w")
        self.encoding_optionmenu = ctk.CTkOptionMenu(app_config_frame, values=['latin-1', 'utf-8', 'cp1252'], variable=self.log_encoding_var)
        self.encoding_optionmenu.grid(row=4, column=1, padx=PADX_MAIN_CONTENT, pady=PADY_MAIN_CONTENT, sticky="ew")


        analysis_config_frame = ctk.CTkFrame(scrollable_content, fg_color="transparent")
        analysis_config_frame.pack(fill="x", padx=20, pady=(15, 10))
        analysis_config_frame.grid_columnconfigure(1, weight=1)

        self.ia_checkbox = ctk.CTkCheckBox(analysis_config_frame, text="Habilitar Análise por IA (requer Ollama)", variable=self.ia_enabled_var, corner_radius=CORNER_RADIUS)
        self.ia_checkbox.grid(row=1, column=0, columnspan=2, padx=PADX_MAIN_CONTENT, pady=PADY_MAIN_CONTENT, sticky="w")
        
        # Indicador de status do Ollama
        self.ollama_status_label = ctk.CTkLabel(analysis_config_frame, text="")
        self.ollama_status_label.grid(row=1, column=1, padx=PADX_MAIN_CONTENT, pady=PADY_MAIN_CONTENT, sticky="e")
        self.update_ollama_status_label()

        ctk.CTkLabel(analysis_config_frame, text="Modelo Ollama (ex: llama3):").grid(row=2, column=0, padx=PADX_MAIN_CONTENT, pady=PADY_MAIN_CONTENT, sticky="w")
        self.entry_ollama_model = ctk.CTkEntry(analysis_config_frame, textvariable=self.ollama_model_var, corner_radius=CORNER_RADIUS)
        self.entry_ollama_model.grid(row=2, column=1, padx=PADX_MAIN_CONTENT, pady=PADY_MAIN_CONTENT, sticky="ew")


        ctk.CTkLabel(analysis_config_frame, text="Gatilhos de Análise (palavras-chave separadas por vírgula):").grid(row=3, column=0, padx=PADX_MAIN_CONTENT, pady=PADY_MAIN_CONTENT, sticky="w")
        self.entry_keywords = ctk.CTkEntry(analysis_config_frame, textvariable=self.keywords_var, corner_radius=CORNER_RADIUS)
        self.entry_keywords.grid(row=3, column=1, padx=PADX_MAIN_CONTENT, pady=PADY_MAIN_CONTENT, sticky="ew")

        ctk.CTkLabel(analysis_config_frame, text="Nº Máximo de Linhas no Log da Tela:").grid(row=4, column=0, padx=PADX_MAIN_CONTENT, pady=PADY_MAIN_CONTENT, sticky="w")
        self.entry_max_lines = ctk.CTkEntry(analysis_config_frame, textvariable=self.max_log_lines_var, corner_radius=CORNER_RADIUS)
        self.entry_max_lines.grid(row=4, column=1, padx=PADX_MAIN_CONTENT, pady=PADY_MAIN_CONTENT, sticky="ew")

        self.capture_evidence_checkbox = ctk.CTkCheckBox(analysis_config_frame, text="Capturar evidências de erro (screenshot + ações)", variable=self.capture_evidence_var, corner_radius=CORNER_RADIUS)
        self.capture_evidence_checkbox.grid(row=5, column=0, columnspan=2, padx=PADX_MAIN_CONTENT, pady=PADY_MAIN_CONTENT, sticky="w")
        
        if not SCREENSHOT_DISPONIVEL:
            self.capture_evidence_checkbox.configure(state='disabled', text="Capturar evidências (pyautogui não instalado)")


    def setup_history_page(self, parent_frame):
        """Cria a interface da página 'Histórico'."""
        parent_frame.grid_columnconfigure(0, weight=0)
        parent_frame.grid_columnconfigure(1, weight=1)
        parent_frame.grid_rowconfigure(0, weight=0)
        parent_frame.grid_rowconfigure(1, weight=1)

        toolbar = self._create_toolbar(parent_frame, "Histórico de Sessões")
        toolbar.grid(row=0, column=0, columnspan=2, padx=PADX_MAIN_CONTENT, pady=(0, PADY_MAIN_CONTENT), sticky="ew")
        
        left_frame = ctk.CTkFrame(parent_frame, fg_color="#333333", corner_radius=12)
        left_frame.grid(row=1, column=0, padx=(PADX_MAIN_CONTENT, PADY_MAIN_CONTENT), pady=(0, PADY_MAIN_CONTENT), sticky="ns")
        left_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(left_frame, text="Sessões Salvas", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=PADX_MAIN_CONTENT, pady=PADY_MAIN_CONTENT)
        self.history_listbox = tk.Listbox(left_frame, bg="#2b2b2b", fg="white", selectbackground="#1f6aa5", borderwidth=0, highlightthickness=0,
                                         font=("Consolas", 10))
        self.history_listbox.grid(row=1, column=0, padx=PADX_MAIN_CONTENT, pady=PADY_MAIN_CONTENT, sticky="ns")
        self.history_listbox.bind("<Double-1>", lambda e: self.load_selected_log())
        
        history_actions_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        history_actions_frame.grid(row=2, column=0, padx=PADX_MAIN_CONTENT, pady=PADY_MAIN_CONTENT)
        ctk.CTkButton(history_actions_frame, text="Carregar", command=lambda: [self.log_action("Botão 'Carregar' (Histórico) clicado."), self.load_selected_log()]).pack(side=tk.LEFT, padx=5)
        ctk.CTkButton(history_actions_frame, text="Exportar 📄", command=lambda: [self.log_action("Botão 'Exportar Log' (Histórico) clicado."), self.export_history_log()]).pack(side=tk.LEFT, padx=5)
        ctk.CTkButton(history_actions_frame, text="Apagar", command=lambda: [self.log_action("Botão 'Apagar' (Histórico) clicado."), self.delete_selected_log()], fg_color="#D32F2F", hover_color="#B71C1C").pack(side=tk.LEFT, padx=5)
        
        right_display_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        right_display_frame.grid(row=1, column=1, padx=(0, PADX_MAIN_CONTENT), pady=(0, PADY_MAIN_CONTENT), sticky="nsew")
        right_display_frame.grid_columnconfigure(0, weight=1)
        right_display_frame.grid_rowconfigure(1, weight=1)
        
        history_search_frame = ctk.CTkFrame(right_display_frame, fg_color="transparent")
        history_search_frame.grid(row=0, column=0, sticky="ew", pady=(0, PADY_MAIN_CONTENT))
        
        self.search_entry_history = ctk.CTkEntry(history_search_frame, textvariable=self.search_term_history, placeholder_text="Buscar no histórico...", corner_radius=CORNER_RADIUS)
        self.search_entry_history.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.search_entry_history.bind("<Return>", lambda e: self.search_in_history())
        self.search_button_history = ctk.CTkButton(history_search_frame, text="🔎", command=self.search_in_history, width=40, corner_radius=CORNER_RADIUS)
        self.search_button_history.pack(side=tk.LEFT)
        
        self.history_display = ctk.CTkTextbox(right_display_frame, wrap=tk.WORD, font=("Consolas", 11), corner_radius=CORNER_RADIUS, border_width=1, fg_color="#333333")
        self.history_display.grid(row=1, column=0, sticky="nsew")
        self.history_display.configure(state=tk.DISABLED)
        self.history_display.tag_config("search_highlight", background="#F9A825", foreground="black")
        
        self.populate_history_listbox()

    def update_ollama_status_label(self):
        if not OLLAMA_DISPONIVEL:
            self.ollama_status_label.configure(text="Ollama: ❌ Não disponível", text_color="red")
        else:
            try:
                # Tenta uma comunicação mais leve, sem um modelo específico
                # Apenas para verificar se o servidor Ollama está de pé.
                ollama.list() 
                self.ollama_status_label.configure(text="Ollama: ✅ Disponível", text_color="green")
            except Exception:
                self.ollama_status_label.configure(text="Ollama: ⚠️ Servidor não responde", text_color="orange")
        
    def process_log_queue(self):
        try:
            batch_size = 0
            while batch_size < 200:
                item = self.log_queue.get_nowait()
                msg_type, content = item.get("type"), item.get("content")
                
                if msg_type == "raw_line":
                    self.log_buffer.append(content)
                    self._extract_connections_from_line(content)
                    if len(self.log_buffer) >= 50 or self.log_queue.empty():
                        self._update_log_display()
                else: 
                    self._update_log_display()
                    if msg_type in ["system_message", "system_error"]:
                        self.display_system_message(content, is_error=(msg_type == "system_error"))
                    elif msg_type == "content_block":
                        self.capture_evidence()
                        threading.Thread(target=self.chamar_analise_avancada, args=(content, self.ollama_model_var.get()), daemon=True).start()
                    elif msg_type == "analysis_result":
                        self.analysis_results_summary_buffer.append(content) 
                        self.display_analysis_result(content)
                batch_size += 1
        except queue.Empty:
            self._update_log_display()
        finally:
            if self.winfo_exists():
                self.after(250, self.process_log_queue)

    def _extract_connections_from_line(self, line):
        """Extrai URLs, hosts, IPs e portas de uma linha de log e armazena em self.detected_connections."""
        url_pattern = r'(?:https?|ftp)://(?:[a-zA-Z0-9\.-]+(?::[0-9]{2,5})?|[0-9]{1,3}(?:\.[0-9]{1,3}){3})(?:/[^\s]*)?'
        host_port_domain_pattern = r'\b(?:[a-zA-Z0-9\.-]+\.(?:com|org|net|br|cloud|io|app|dev|biz|info|ws|co|gov|mil|edu)(?:\:[0-9]{2,5})?)\b'
        ip_port_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{2,5}\b'
        jdbc_url_pattern = r'jdbc:[^=;]+(?:=|url=)([^\s,;]+)'

        combined_pattern = re.compile(f'({url_pattern})|({host_port_domain_pattern})|({ip_port_pattern})|({jdbc_url_pattern})', re.IGNORECASE)

        matches = combined_pattern.finditer(line)
        for match in matches:
            captured_value = next(g for g in match.groups() if g is not None)
            
            if captured_value:
                normalized_value = captured_value.strip().lower()
                
                if normalized_value and \
                   not normalized_value.startswith("null") and \
                   not normalized_value.startswith("undefined") and \
                   not normalized_value.endswith((".jar", ".exe", ".log", ".txt", ".sql", ".conf", ".xml")) and \
                   not re.match(r'^\d+(\s+de\s+)?\d+?$', normalized_value) and \
                   not normalized_value.startswith("./"):
                    
                    if "jdbc:" in normalized_value and "user=" in normalized_value:
                        normalized_value = re.sub(r'(user|password)=[^;,\s]+', 'user=******, password=******', normalized_value)
                        
                    self.detected_connections.add(normalized_value)

    def _update_log_display(self):
        if not self.log_buffer:
            return
        
        full_text = "".join(self.log_buffer)
        self.log_buffer.clear()
        
        self.log_textbox.configure(state=tk.NORMAL)
        self.log_textbox.insert(tk.END, full_text)

        try:
            max_lines = self.max_log_lines_var.get()
            line_count = int(self.log_textbox.index('end-1c').split('.')[0])
            if line_count > max_lines:
                lines_to_delete = line_count - max_lines
                self.log_textbox.delete('1.0', f'{lines_to_delete + 1}.0')
        except (ValueError, tk.TclError):
            pass

        self.log_textbox.see(tk.END)
        self.log_textbox.configure(state=tk.DISABLED)

        self.append_to_history_log(full_text)

    def chamar_analise_avancada(self, bloco, ollama_model_name):
        if self.analysis_lock.acquire(blocking=False):
            try:
                self.log_action("Tentando análise de bloco (base de conhecimento e IA se habilitada).")
                resultado = analisar_bloco_com_ia(bloco, ia_enabled=self.ia_enabled_var.get(), ollama_model=ollama_model_name)
                
                # Apenas adiciona à fila se um resultado (não None) foi retornado
                if resultado: 
                    self.log_queue.put({"type": "analysis_result", "content": resultado})
                else:
                    # Se 'resultado' é None, significa que a IA está desabilitada E nenhum padrão local foi mapeado.
                    # Neste caso, não exibimos um bloco de análise.
                    # Apenas logamos a ação internamente para depuração.
                    self.log_action("Análise de IA desabilitada e sem padrão mapeado para este bloco. Análise pulada.")
            finally:
                self.analysis_lock.release()
        else:
            self.log_action("Análise de IA ignorada (processo já em andamento).")

    def save_config(self):
        self.log_action("Configurações salvas automaticamente.")
        config_data = {
            "command": self.command_var.get(), 
            "workdir": self.workdir_var.get(), 
            "keywords": self.keywords_var.get(),
            "ia_enabled": self.ia_enabled_var.get(),
            "ollama_model": self.ollama_model_var.get(),
            "log_encoding": self.log_encoding_var.get(),
            "max_log_lines": self.max_log_lines_var.get(),
            "capture_evidence": self.capture_evidence_var.get()
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(config_data, f, indent=4)
            print("Configurações salvas automaticamente.")
        except Exception as e:
            print(f"Erro ao salvar configuração automaticamente: {e}")
            self.log_action(f"ERRO: Falha ao salvar configuração automaticamente: {e}")
        
    def load_config(self):
        if not os.path.exists(CONFIG_FILE): 
            self.keywords_var.set("ERROR, WARN, GRAVE, Falha, Exception, Timeout, not found, dir not exists, N\\u00C3O DEFINIDO, timezone")
            self.ollama_model_var.set('llama31-8b-f32:latest')
            self.log_encoding_var.set('latin-1')
            return
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f: config_data = json.load(f)
            self.command_var.set(config_data.get("command", ""))
            self.workdir_var.set(config_data.get("workdir", ""))
            self.keywords_var.set(config_data.get("keywords", "ERROR, WARN, GRAVE, Falha, Exception, Timeout, not found, dir not exists, N\\u00C3O DEFINIDO, timezone"))
            self.ia_enabled_var.set(config_data.get("ia_enabled", True))
            self.ollama_model_var.set(config_data.get("ollama_model", 'llama31-8b-f32:latest'))
            self.log_encoding_var.set(config_data.get("log_encoding", 'latin-1'))
            self.max_log_lines_var.set(config_data.get("max_log_lines", 3000))
            self.capture_evidence_var.set(config_data.get("capture_evidence", True))
        except Exception as e: 
            print(f"Erro ao carregar configuração: {e}")
            self.keywords_var.set("ERROR, WARN, GRAVE, Falha, Exception, Timeout, not found, dir not exists, N\\u00C3O DEFINIDO, timezone")
            self.ia_enabled_var.set(True)
            self.ollama_model_var.set('llama31-8b-f32:latest')
            self.log_encoding_var.set('latin-1')
            self.max_log_lines_var.set(3000)
            self.capture_evidence_var.set(True)

    def set_ui_state(self, monitoring: bool):
        state = 'disabled' if monitoring else 'normal'
        self.start_button.configure(state='disabled' if monitoring else 'normal')
        self.stop_button.configure(state='normal' if monitoring else 'disabled')
        if hasattr(self, 'browse_button'): self.browse_button.configure(state=state)
        if hasattr(self, 'entry_keywords'): self.entry_keywords.configure(state=state)
        if hasattr(self, 'entry_command'): self.entry_command.configure(state=state)
        if hasattr(self, 'entry_workdir'): self.entry_workdir.configure(state=state)
        if hasattr(self, 'ia_checkbox'): self.ia_checkbox.configure(state=state)
        if hasattr(self, 'entry_ollama_model'): self.entry_ollama_model.configure(state=state)
        if hasattr(self, 'encoding_optionmenu'): self.encoding_optionmenu.configure(state=state)
        if hasattr(self, 'entry_max_lines'): self.entry_max_lines.configure(state=state)
        if hasattr(self, 'capture_evidence_checkbox') and SCREENSHOT_DISPONIVEL: # Apenas muda se pyautogui estiver disponível
            self.capture_evidence_checkbox.configure(state=state)

    def escolher_executavel(self):
        self.log_action("Botão 'Procurar Executável' clicado.")
        filepath = filedialog.askopenfilename(title="Selecione o executável da aplicação", filetypes=[("Executáveis", "*.jar *.exe"), ("Todos os Arquivos", "*.*")])
        if not filepath:
            self.log_action("Seleção de arquivo cancelada.")
            return
        
        self.log_action(f"Arquivo selecionado: {filepath}")
        workdir = os.path.dirname(filepath)
        self.workdir_var.set(workdir.replace("/", "\\"))
        if filepath.lower().endswith(".jar"):
            command = f'java -jar "{filepath}"'
        else:
            command = f'"{filepath}"'
        self.command_var.set(command)

    def load_selected_log(self):
        selected_indices = self.history_listbox.curselection()
        if not selected_indices: return
        filename = self.history_listbox.get(selected_indices[0])
        self.log_action(f"Carregando log do histórico: {filename}")
        filepath = os.path.join(HISTORY_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f: content = f.read()
            self.last_search_pos_history = "1.0"
            self.last_searched_term_history = ""
            self.search_term_history.set("")
            self.history_display.configure(state=tk.NORMAL)
            self.history_display.delete("1.0", tk.END)
            self.history_display.insert("1.0", content)
            self.history_display.configure(state=tk.DISABLED)
        except Exception as e: messagebox.showerror("Erro ao Carregar", f"Não foi possível ler o arquivo de log:\n{e}")

    def on_closing(self):
        self.log_action("Aplicação fechada.")
        if self.auto_save_job:
            self.after_cancel(self.auto_save_job)
        self.save_config()
        self.stop_monitoring() 
        self.destroy()

    def search_in_monitor(self, event=None):
        term = self.search_term_monitor.get()
        if not term: return
        self.log_action(f"Busca no monitor pelo termo: '{term}'")
        self._perform_search(self.log_textbox, self.search_term_monitor, "last_search_pos_monitor", "last_searched_term_monitor")

    def search_in_history(self, event=None):
        term = self.search_term_history.get()
        if not term: return
        self.log_action(f"Busca no histórico pelo termo: '{term}'")
        self._perform_search(self.history_display, self.search_term_history, "last_search_pos_history", "last_searched_term_history")

    def delete_selected_log(self):
        selected_indices = self.history_listbox.curselection()
        if not selected_indices: return
        filename = self.history_listbox.get(selected_indices[0])
        self.log_action(f"Tentativa de apagar o log: '{filename}'")
        if messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja apagar permanentemente o arquivo '{filename}'?"):
            try:
                os.remove(os.path.join(HISTORY_DIR, filename))
                self.populate_history_listbox()
                self.history_display.configure(state=tk.NORMAL)
                self.history_display.delete("1.0", tk.END)
                self.history_display.configure(state=tk.DISABLED)
                self.log_action(f"Log '{filename}' apagado com sucesso.")
            except Exception as e: messagebox.showerror("Erro ao Apagar", f"Não foi possível apagar o arquivo:\n{e}")
        else:
            self.log_action("Exclusão de log cancelada.")

    def _export_log(self, text_widget):
        try:
            text_widget.configure(state=tk.NORMAL)
            content = text_widget.get("1.0", tk.END)
        finally:
            text_widget.configure(state=tk.DISABLED)
        if not content.strip():
            messagebox.showinfo("Exportar Log", "Não há conteúdo para exportar.")
            return
        try:
            filepath = filedialog.asksaveasfilename(
                title="Salvar Log Como...",
                defaultextension=".log",
                filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
            )
            if not filepath:
                self.log_action("Exportação de log cancelada.")
                return 
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            self.log_action(f"Log exportado para: {filepath}")
            messagebox.showinfo("Sucesso", f"Log exportado com sucesso para:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Erro ao Exportar", f"Não foi possível salvar o arquivo de log.\n\nErro: {e}")
            
    def export_monitor_log(self): self._export_log(self.log_textbox)
    def export_history_log(self): self._export_log(self.history_display)    
    
    def _perform_search(self, textbox, search_term_var, last_pos_attr, last_term_attr):
        term = search_term_var.get()
        if not term: return
        last_pos = getattr(self, last_pos_attr)
        last_term = getattr(self, last_term_attr)
        
        textbox.configure(state=tk.NORMAL)
        textbox.tag_remove("search_highlight", "1.0", tk.END)
        
        if term != last_term:
            last_pos = "1.0"
            setattr(self, last_term_attr, term)
        
        pos = textbox.search(term, last_pos, stopindex=tk.END, nocase=True)
        if pos:
            end_pos = f"{pos}+{len(term)}c"
            textbox.tag_add("search_highlight", pos, end_pos)
            textbox.see(pos)
            setattr(self, last_pos_attr, end_pos)
        else:
            if messagebox.askyesno("Fim da Busca", "Nenhuma outra ocorrência encontrada. Deseja buscar desde o início?"):
                self.log_action("Busca reiniciada do início.")
                setattr(self, last_pos_attr, "1.0")
                self._perform_search(textbox, search_term_var, last_pos_attr, last_term_attr)
            else:
                pass 
        textbox.configure(state=tk.DISABLED)

    def stream_reader_worker(self, process, keywords_str, encoding_val):
        keywords_list = [k.strip().lower() for k in keywords_str.split(',') if k.strip()]
        
        trigger_patterns = [r'\[ERROR\]', r'\[WARN\]', r'GRAVE:', r'Falha ao carregar configurações de proxy', 
                            r'N\\u00C3O DEFINIDO NO ARQUIVO \.conf', r'timezone',
                            r'Levou \d+ milis para calcular ST', 
                            r'Levou \d+ milis para carregar os dados',
                            r'Conectado em', r'Autenticado em', 
                            r'sucesso para faturamento', r'Pedidos registrados com sucesso',
                            r'slf4j LogbackLogger binder not found'
                           ] + [re.escape(k) for k in keywords_list if k.strip()]
        trigger_regex = re.compile('|'.join(trigger_patterns), re.IGNORECASE)

        line_buffer = deque(maxlen=50) 

        for line in iter(process.stdout.readline, ''):
            if not self.is_monitoring: break

            self._extract_connections_from_line(line)
            line_buffer.append(line) 

            if trigger_regex.search(line):
                context_before_trigger = list(line_buffer)[:-1]
                error_block_content = "".join(context_before_trigger[-15:]) + line
                
                for _ in range(30): 
                    try:
                        next_line = next(iter(process.stdout.readline, ''))
                        if not next_line: break
                        error_block_content += next_line
                    except StopIteration:
                        break
                self.log_queue.put({"type": "content_block", "content": error_block_content})

            self.log_queue.put({"type": "raw_line", "content": line})


        process.stdout.close()
        if self.is_monitoring:
            self.log_queue.put({"type": "system_message", "content": "--- [ APLICAÇÃO EXTERNA FINALIZADA ] ---"})
            self.after(0, self.stop_monitoring)

    def start_monitoring(self):
        command_str = self.command_var.get()
        workdir = self.workdir_var.get()
        log_encoding = self.log_encoding_var.get()

        if not command_str or not workdir: 
            messagebox.showerror("Erro de Configuração", "Vá para a aba 'Configurações' e selecione a aplicação e o diretório de trabalho.")
            return
        if not os.path.isdir(workdir): 
            messagebox.showerror("Erro", f"O diretório de trabalho é inválido:\n{workdir}")
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current_session_filepath = os.path.join(HISTORY_DIR, f"sessao_{timestamp}.log")
        
        self.is_monitoring = True
        self.limpar_log()
        self.log_queue.put({"type": "system_message", "content": f"--- [ INICIANDO PROCESSO: {command_str} ] ---"})
        
        self.analysis_results_summary_buffer.clear()
        self.detected_connections.clear()

        try:
            args = shlex.split(command_str)
            creation_flags_value = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            self.java_process = subprocess.Popen(args, cwd=workdir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding=log_encoding, errors='replace', shell=False, creationflags=creation_flags_value)
            self.process_thread = threading.Thread(target=self.stream_reader_worker, args=(self.java_process, self.keywords_var.get(), log_encoding), daemon=True)
            self.process_thread.start()
            self.set_ui_state(monitoring=True)
        except FileNotFoundError:
            self.log_queue.put({"type": "system_error", "content": f"ERRO: Comando ou arquivo não encontrado. Verifique o caminho em Configurações: {command_str}"})
            messagebox.showerror("Erro de Execução", f"O comando ou arquivo '{command_str}' não foi encontrado. Verifique o caminho nas configurações.")
            self.stop_monitoring()
        except Exception as e:
            self.log_queue.put({"type": "system_error", "content": f"ERRO ao iniciar o processo: {e}"})
            messagebox.showerror("Erro de Execução", f"Ocorreu um erro inesperado ao iniciar o processo:\n{e}")
            self.stop_monitoring()

    def stop_monitoring(self):
        if not self.is_monitoring:
            return

        self.is_monitoring = False
        if self.java_process and self.java_process.poll() is None:
            self.log_queue.put({"type": "system_message", "content": "--- [ FINALIZANDO PROCESSO EXTERNO... ] ---"})
            try:
                self.java_process.terminate()
                self.java_process.wait(timeout=5)
                if self.java_process.poll() is None:
                    # Tenta forçar o kill se não terminar em 5 segundos
                    kill_command = f"taskkill /F /T /PID {self.java_process.pid}" if os.name == 'nt' else f"kill -9 {self.java_process.pid}"
                    subprocess.run(shlex.split(kill_command), check=False, capture_output=True, creationflags=0x08000000 if os.name == 'nt' else 0)
            except Exception as e:
                self.log_queue.put({"type": "system_error", "content": f"ERRO ao tentar encerrar o processo: {e}"})
            finally:
                self.java_process = None
        
        self.set_ui_state(monitoring=False)
        self.populate_history_listbox()
        self.log_queue.put({"type": "system_message", "content": "--- [ MONITORAMENTO PARADO ] ---"})
        self.generate_analysis_summary()

    def generate_analysis_summary(self):
        """Gera e exibe um resumo consolidado das análises e conexões diretamente no log principal."""
        
        if self.analysis_results_summary_buffer or self.detected_connections: # Só gera resumo se houver algo
            self.log_textbox.configure(state=tk.NORMAL)
            
            # Cabeçalho principal do resumo
            self.log_textbox.insert(tk.END, "\n" + "="*80 + "\n", "summary_header")
            self.log_textbox.insert(tk.END, "📊 RESUMO DA SESSÃO DE ANÁLISE 📊\n".upper(), "summary_header")
            self.log_textbox.insert(tk.END, "="*80 + "\n\n", "summary_header")

            # Seção de Análises de Eventos
            if self.analysis_results_summary_buffer:
                grouped_results = {
                    "ERRO": [],
                    "AVISO": [],
                    "INFO DE PERFORMANCE": [],
                    "INFO": [],
                    "SUCESSO": [],
                    "OLLAMA_INDISPONIVEL": [],
                    "OUTROS": []
                }

                for result in self.analysis_results_summary_buffer:
                    status = result.get("status", "OUTROS").upper()
                    summary = result.get("resumo", "Resumo não disponível")
                    
                    if "ERRO" in status:
                        grouped_results["ERRO"].append(summary)
                    elif "AVISO" in status or "WARN" in status:
                        grouped_results["AVISO"].append(summary)
                    elif "INFO DE PERFORMANCE" in status:
                        grouped_results["INFO DE PERFORMANCE"].append(summary)
                    elif "INFO" in status:
                        grouped_results["INFO"].append(summary)
                    elif "SUCESSO" in status:
                        grouped_results["SUCESSO"].append(summary)
                    elif "OLLAMA_INDISPONIVEL" in status:
                        grouped_results["OLLAMA_INDISPONIVEL"].append(summary)
                    else:
                        grouped_results["OUTROS"].append(summary)

                ordered_categories = ["ERRO", "AVISO", "INFO DE PERFORMANCE", "SUCESSO", "INFO", "OLLAMA_INDISPONIVEL", "OUTROS"]
                
                self.log_textbox.insert(tk.END, "--- ANÁLISES DE EVENTOS ---\n\n", "summary_header")

                for category in ordered_categories:
                    items = grouped_results[category]
                    if items:
                        header_text = f"  >> {category} ({len(items)} ocorrências)\n"
                        # Aplicar cor com base na categoria
                        tag = "info"
                        if "ERRO" in category: tag = "erro"
                        elif "AVISO" in category: tag = "aviso"
                        
                        self.log_textbox.insert(tk.END, header_text, tag)
                        # Usa set para obter resumos únicos
                        for i, item in enumerate(list(set(items))[:5]): 
                            self.log_textbox.insert(tk.END, f"    - {item}\n", tag)
                        if len(set(items)) > 5:
                            self.log_textbox.insert(tk.END, "    ... e mais.\n", tag)
                self.log_textbox.insert(tk.END, "\n") # Espaço após as categorias

            else:
                self.log_textbox.insert(tk.END, "--- ANÁLISES DE EVENTOS ---\n\n", "summary_header")
                self.log_textbox.insert(tk.END, "--- Nenhuma análise de evento detectada nesta sessão. ---\n\n", "info")


            # Seção de Conexões de Rede
            self.log_textbox.insert(tk.END, "--- CONEXÕES DE REDE DETECTADAS ---\n\n", "summary_header")
            if self.detected_connections:
                self.log_textbox.insert(tk.END, f"  ({len(self.detected_connections)} endereços/URLs únicos):\n", "info")
                for conn in sorted(list(self.detected_connections)): 
                    self.log_textbox.insert(tk.END, f"    - {conn}\n", "info")
                self.log_textbox.insert(tk.END, "\n", "info")
            else:
                self.log_textbox.insert(tk.END, "--- Nenhuma conexão de rede detectada nesta sessão. ---\n\n", "info")

            self.log_textbox.insert(tk.END, f"\n{'='*80}\n\n", "summary_header")
            self.log_textbox.see(tk.END)
            self.log_textbox.configure(state=tk.DISABLED)
            # Salvando o resumo no log de histórico
            # Para o histórico, o ideal é salvar o texto completo do resumo, não os "parts" crus
            # Pega as últimas 2000 chars (ou mais se necessário) para garantir que todo o resumo seja capturado
            full_summary_text_for_history = self.log_textbox.get("end-1c - 2000 chars", "end-1c") 
            if "RESUMO DA SESSÃO DE ANÁLISE" in full_summary_text_for_history: # Verifica se o resumo está lá
                start_index = full_summary_text_for_history.find("="*80)
                if start_index != -1:
                    full_summary_text_for_history = full_summary_text_for_history[start_index:]
                    self.append_to_history_log(full_summary_text_for_history)

        else:
            self.log_queue.put({"type": "system_message", "content": "--- Nenhuma análise ou conexão relevante detectada nesta sessão. ---"})
            
        self.analysis_results_summary_buffer.clear()
        self.detected_connections.clear() 
    

    def limpar_log(self):
        self.log_textbox.configure(state=tk.NORMAL)
        self.log_textbox.delete("1.0", tk.END)
        self.log_textbox.configure(state=tk.DISABLED)
        self.last_search_pos_monitor = "1.0"
        self.last_searched_term_monitor = ""
        self.log_buffer.clear()
        self.analysis_results_summary_buffer.clear()
        self.detected_connections.clear() 

    def append_to_history_log(self, text):
        if self.current_session_filepath:
            try:
                with open(self.current_session_filepath, 'a', encoding='utf-8') as f: f.write(text)
            except Exception as e: print(f"Erro ao salvar no histórico: {e}")

    def display_system_message(self, message, is_error=False):
        formatted_message = f"\n>> {message.strip()}\n"
        self.log_textbox.configure(state=tk.NORMAL)
        self.log_textbox.insert(tk.END, formatted_message, "erro" if is_error else "info")
        self.log_textbox.see(tk.END)
        self.log_textbox.configure(state=tk.DISABLED)
        self.append_to_history_log(formatted_message)

    def display_analysis_result(self, result_dict):
        status = result_dict.get("status", "N/A").upper()
        summary = result_dict.get("resumo", "N/A")
        suggestion = result_dict.get("sugestao", "N/A")
        causa_raiz = result_dict.get("causa_raiz", "N/A")
        componente = result_dict.get("componente_afetado", "N/A")
        id_entidade = result_dict.get("id_entidade", "N/A")
        tempo_execucao = result_dict.get("tempo_execucao_ms", "N/A")
        
        tag = "info" 
        if "ERRO" in status:
            tag = "erro"
        elif "AVISO" in status or "WARN" in status or "OLLAMA_INDISPONIVEL" in status:
            tag = "aviso"
        elif "SUCESSO" in status:
            tag = "info" 

        output_block = [f"\n{'='*80}\n", f"🤖 ANÁLISE DE EVENTO 🤖\n".upper()]
        output_block.append(f"Status: {status}\n")
        output_block.append(f"Resumo: {summary}\n")
        if causa_raiz != "N/A": output_block.append(f"Causa Raiz: {causa_raiz}\n")
        if componente != "N/A": output_block.append(f"Componente: {componente}\n")
        if id_entidade != "N/A": output_block.append(f"ID Entidade: {id_entidade}\n")
        if tempo_execucao != "N/A": output_block.append(f"Tempo Execução: {tempo_execucao} ms\n")
        output_block.append(f"Sugestão: {suggestion}\n")
        output_block.append(f"{'='*80}\n\n")
        
        self.log_textbox.configure(state=tk.NORMAL)
        self.log_textbox.insert(tk.END, "".join(output_block), tag)
        self.log_textbox.see(tk.END)
        self.log_textbox.configure(state=tk.DISABLED)
        self.append_to_history_log("".join(output_block))
        
    def populate_history_listbox(self):
        if not hasattr(self, 'history_listbox'):
            return 
            
        self.history_listbox.delete(0, tk.END)
        if not os.path.exists(HISTORY_DIR): return
        try:
            files = sorted([f for f in os.listdir(HISTORY_DIR) if f.endswith(".log")], key=lambda f: os.path.getmtime(os.path.join(HISTORY_DIR, f)), reverse=True)
            for filename in files: self.history_listbox.insert(tk.END, filename)
        except Exception as e: messagebox.showerror("Erro de Histórico", f"Não foi possível ler o diretório de histórico: {e}")

# ==============================================================================
# BLOCO DE EXECUÇÃO PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    libs_necessarias = ['customtkinter']
    
    if SCREENSHOT_DISPONIVEL: libs_necessarias.append('pyautogui')

    faltando = []
    # Verifica Pillow separadamente pois é uma dependência implícita de customtkinter e pyautogui
    try:
        from PIL import Image
    except ImportError:
        faltando.append('Pillow')

    for lib in libs_necessarias:
        try:
            __import__(lib)
        except ImportError:
            faltando.append(lib)

    if faltando:
        faltando_str = ' '.join(set(faltando)) # Usa set para remover duplicatas e join com espaço
        
        install_cmd = f"pip install {faltando_str}"
        
        # Adiciona instruções para Ollama e modelos
        ollama_instructions = ""
        if 'ollama' in faltando_str:
            ollama_instructions += "\n\nPara Ollama:\n"
            ollama_instructions += "1. Baixe e instale o Ollama de https://ollama.com/\n"
            ollama_instructions += "2. Execute 'ollama run llama2' ou 'ollama run llama3' no terminal para baixar um modelo."

        messagebox.showerror(
            "Dependências Faltando",
            f"As seguintes bibliotecas Python são necessárias:\n\n"
            f"  -> {', '.join(set(faltando))}\n\n"
            f"Instale-as com:\n"
            f"  {install_cmd}"
            f"{ollama_instructions}\n\n"
            f"Certifique-se de ter o Python e o pip instalados e configurados corretamente."
        )
        exit(1)

    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except (ImportError, AttributeError):
            pass

    app = LogMonitorAppModern()
    app.mainloop()
    #teste