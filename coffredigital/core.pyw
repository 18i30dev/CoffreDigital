import customtkinter as ctk
import sqlite3
import os
import time
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import string
import random
import secrets
import ctypes
import sys


# Diretório base do projeto (funciona tanto em desenvolvimento quanto em executável PyInstaller)
if getattr(sys, 'frozen', False):
    # Executável PyInstaller: usa o diretório do .exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Execução via Python: usa o diretório do projeto (um nível acima deste arquivo)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Garante que a pasta de dados exista (necessario no executavel PyInstaller)
DATA_DIR = os.path.join(BASE_DIR, "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)


def resource_path(caminho_relativo):
    """Resolve caminho de recursos (icone, etc.) em desenvolvimento e no .exe."""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        return os.path.join(base, caminho_relativo)
    return os.path.join(BASE_DIR, caminho_relativo)


# ============================
# Dialogs personalizados (estilo CustomTkinter)
# Substituem messagebox e simpledialog nativas do tkinter
# ============================

class CTkInputDialog(ctk.CTkToplevel):
    """Dialog de entrada de texto no estilo CustomTkinter.
    Substitui simpledialog.askstring. Retorna a string digitada ou None se cancelado.
    """
    def __init__(self, title, prompt, show=None):
        super().__init__()
        self.title(title)
        self.geometry("400x220")
        self.resizable(False, False)
        self.result = None

        ctk.CTkLabel(self, text=prompt, font=("Arial", 13)).pack(pady=(25, 10))
        self.entry = ctk.CTkEntry(self, width=300, show=show)
        self.entry.pack(pady=5)
        self.entry.focus()
        self.entry.bind("<Return>", lambda e: self._confirm())

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="OK", command=self._confirm, width=100).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancelar", command=self.destroy, width=100,
                      fg_color="gray40", hover_color="gray30").pack(side="left", padx=10)

        self.transient(self.master)
        self.grab_set()
        self.wait_window(self)

    def _confirm(self):
        self.result = self.entry.get()
        self.destroy()


class CTkMessageDialog(ctk.CTkToplevel):
    """Dialog de mensagem (info/aviso/erro) no estilo CustomTkinter.
    Substitui messagebox.showinfo/showwarning/showerror.
    """
    def __init__(self, title, message, tipo="info"):
        super().__init__()
        self.title(title)
        self.geometry("400x200")
        self.resizable(False, False)

        cor = {"info": ("#3B8ED0", "#1F6AA5"), "warning": ("#CC8500", "#B46300"),
               "error": ("#D43D3D", "#A82A2A")}.get(tipo, ("#3B8ED0", "#1F6AA5"))

        ctk.CTkLabel(self, text=message, font=("Arial", 13), wraplength=350).pack(pady=(30, 25))
        ctk.CTkButton(self, text="OK", command=self.destroy, width=100,
                      fg_color=cor[0], hover_color=cor[1]).pack(pady=10)

        self.transient(self.master)
        self.grab_set()
        self.wait_window(self)


class CTkConfirmDialog(ctk.CTkToplevel):
    """Dialog de confirmacao Sim/Nao no estilo CustomTkinter.
    Substitui messagebox.askyesno. Retorna True se confirmou, False caso contrario.
    """
    def __init__(self, title, message):
        super().__init__()
        self.title(title)
        self.geometry("400x200")
        self.resizable(False, False)
        self.result = False

        ctk.CTkLabel(self, text=message, font=("Arial", 13), wraplength=350).pack(pady=(30, 20))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Sim", command=self._sim, width=100,
                      fg_color=("red", "darkred"), hover_color=("darkred", "#8B0000")).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Nao", command=self.destroy, width=100,
                      fg_color="gray40", hover_color="gray30").pack(side="left", padx=10)

        self.transient(self.master)
        self.grab_set()
        self.wait_window(self)

    def _sim(self):
        self.result = True
        self.destroy()

RECOVERY_ARQUIVO = os.path.join(BASE_DIR, "data", "recovery.key")
SALT_ARQUIVO = os.path.join(BASE_DIR, "data", "cofre.salt")


def carregar_ou_gerar_salt():
    """Carrega o salt salvo ou gera um novo aleatorio na primeira execucao."""
    if os.path.exists(SALT_ARQUIVO):
        with open(SALT_ARQUIVO, "rb") as f:
            return f.read()
    salt = os.urandom(16)
    with open(SALT_ARQUIVO, "wb") as f:
        f.write(salt)
    return salt


def gerar_chave_recuperacao():
    """Gera uma chave de recuperacao aleatoria (32 caracteres hexadecimais)."""
    return secrets.token_hex(16)


def _derivar_chave_recovery(recovery_key, salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000
    )
    return base64.urlsafe_b64encode(kdf.derive(recovery_key.encode()))


def salvar_recovery(fernet_obj, recovery_key):
    """Salva a chave Fernet criptografada pela chave de recuperacao."""
    salt = os.urandom(16)
    chave_recovery = _derivar_chave_recovery(recovery_key, salt)
    fernet_recovery = Fernet(chave_recovery)
    criptografado = fernet_recovery.encrypt(fernet_obj._signing_key)
    with open(RECOVERY_ARQUIVO, "wb") as f:
        f.write(base64.b64encode(salt) + b"\n")
        f.write(base64.b64encode(criptografado))


def tentar_recuperacao(recovery_key):
    """Tenta recuperar a chave Fernet usando a chave de recuperacao.
    Retorna a chave Fernet (bytes) se estiver correta, senao None."""
    if not os.path.exists(RECOVERY_ARQUIVO):
        return None
    with open(RECOVERY_ARQUIVO, "rb") as f:
        conteudo = f.read()
    partes = conteudo.split(b"\n")
    if len(partes) < 2:
        return None
    try:
        salt = base64.b64decode(partes[0])
        criptografado = base64.b64decode(partes[1])
    except Exception:
        return None
    chave_recovery = _derivar_chave_recovery(recovery_key, salt)
    fernet_recovery = Fernet(chave_recovery)
    try:
        signing_key = fernet_recovery.decrypt(criptografado)
        return signing_key
    except Exception:
        return None


RECOVERY_VISUAL_ARQUIVO = os.path.join(BASE_DIR, "data", "recovery_view.key")


def salvar_recovery_visual(fernet_obj, recovery_key):
    """Salva a chave de recuperacao criptografada com a chave Fernet atual (para visualizacao posterior com senha mestre)."""
    criptografado = fernet_obj.encrypt(recovery_key.encode())
    with open(RECOVERY_VISUAL_ARQUIVO, "wb") as f:
        f.write(base64.b64encode(criptografado))


def carregar_recovery_visual(fernet_obj):
    """Lê e descriptografa a chave de recuperacao armazenada para visualizacao com a senha mestre atual."""
    if not os.path.exists(RECOVERY_VISUAL_ARQUIVO):
        return None
    with open(RECOVERY_VISUAL_ARQUIVO, "rb") as f:
        criptografado = base64.b64decode(f.read())
    try:
        return fernet_obj.decrypt(criptografado).decode()
    except Exception:
        return None


# ----------------------------
# Unica instancia (single instance)
# ----------------------------
MUTEX_NAME = "CoffreDigitalSingleInstanceMutex"
mutex_handle = None


def outra_instancia_rodando():
    """Verifica se ja existe uma instancia do Coffre Digital rodando."""
    global mutex_handle
    kernel32 = ctypes.windll.kernel32
    mutex_handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    return kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS


def restaurar_janela_existente():
    """Tenta restaurar a janela existente da outra instancia."""
    user32 = ctypes.windll.user32
    titulos = ["Coffre Digital - Minhas Senhas", "Coffre Digital - Login"]
    for titulo in titulos:
        hwnd = user32.FindWindowW(None, titulo)
        if hwnd:
            user32.ShowWindow(hwnd, 9)   # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            # Reposiciona para coordenadas visiveis
            user32.SetWindowPos(hwnd, 0, 100, 100, 0, 0,
                                0x0001 | 0x0004 | 0x0040)  # SWP_NOSIZE | SWP_NOZORDER | SWP_SHOWWINDOW
            return True
    return False


def liberar_mutex():
    """Libera o mutex ao encerrar o programa."""
    global mutex_handle
    if mutex_handle:
        ctypes.windll.kernel32.CloseHandle(mutex_handle)
        mutex_handle = None


# ----------------------------
# Configuracao visual
# ----------------------------
ctk.set_appearance_mode("dark")   # Tema escuro
ctk.set_default_color_theme("blue")


class BancoSenhas:
    """Gerencia o arquivo local (SQLite) e a criptografia das senhas."""

    def __init__(self, arquivo=None, chave_mestre="", chave_fernet_direta=None, salt=None):
        if arquivo is None:
            arquivo = os.path.join(BASE_DIR, "data", "cofre.db")
        self.arquivo = arquivo
        self.chave_mestre = chave_mestre
        self.fernet = None          # Objeto que criptografa e descriptografa
        self.conexao = None         # Conexao com o banco SQLite
        self.salt = salt or carregar_ou_gerar_salt()

        if chave_fernet_direta:
            # Usado no processo de recuperacao de senha mestre
            self.fernet = Fernet(chave_fernet_direta)
            self._conectar()
            self._criar_tabela()
        elif chave_mestre:
            self._inicializar_criptografia()
            self._conectar()
            self._criar_tabela()

    def _inicializar_criptografia(self):
        """Transforma a senha mestre em uma chave de criptografia Fernet."""
        salt = self.salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000
        )
        chave = base64.urlsafe_b64encode(kdf.derive(self.chave_mestre.encode()))
        self.fernet = Fernet(chave)

    def _conectar(self):
        self.conexao = sqlite3.connect(self.arquivo)

    def _criar_tabela(self):
        """Cria a tabela se ainda nao existir e garante coluna de exclusao."""
        cursor = self.conexao.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS senhas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                servico TEXT NOT NULL,
                usuario TEXT,
                senha_criptografada TEXT NOT NULL,
                excluido INTEGER DEFAULT 0
            )
        """)
        try:
            cursor.execute("ALTER TABLE senhas ADD COLUMN excluido INTEGER DEFAULT 0")
        except Exception:
            pass
        self.conexao.commit()

    def adicionar(self, servico, usuario, senha):
        """Salva uma senha criptografada no banco."""
        senha_cript = self.fernet.encrypt(senha.encode()).decode()
        cursor = self.conexao.cursor()
        cursor.execute(
            "INSERT INTO senhas (servico, usuario, senha_criptografada) VALUES (?, ?, ?)",
            (servico, usuario, senha_cript)
        )
        self.conexao.commit()

    def listar_todas(self):
        """Retorna todas as senhas, incluindo as marcadas como excluida."""
        cursor = self.conexao.cursor()
        cursor.execute("SELECT id, servico, usuario, senha_criptografada, excluido FROM senhas")
        linhas = cursor.fetchall()
        resultado = []
        for linha in linhas:
            id_, servico, usuario, senha_cript, excluido = linha
            senha = self.fernet.decrypt(senha_cript.encode()).decode()
            resultado.append((id_, servico, usuario, senha, bool(excluido)))
        return resultado

    def listar(self):
        """Retorna apenas as senhas nao excluidas (para exibir na lista principal)."""
        cursor = self.conexao.cursor()
        cursor.execute("SELECT id, servico, usuario, senha_criptografada FROM senhas WHERE excluido = 0")
        linhas = cursor.fetchall()
        resultado = []
        for linha in linhas:
            id_, servico, usuario, senha_cript = linha
            senha = self.fernet.decrypt(senha_cript.encode()).decode()
            resultado.append((id_, servico, usuario, senha))
        return resultado

    def excluir(self, id_):
        """Marca a entrada como excluida (soft delete) sem apagar do banco."""
        cursor = self.conexao.cursor()
        cursor.execute("UPDATE senhas SET excluido = 1 WHERE id=?", (id_,))
        self.conexao.commit()
class TelaLogin(ctk.CTkToplevel):
    """Primeira janela: pede a senha mestre para desbloquear o cofre."""

    LIMITE_TENTATIVAS = 5
    TEMPO_BLOQUEIO_MS = 900000  # 15 minutos

    def __init__(self, master):
        super().__init__(master)
        self.title("Coffre Digital - Login")
        self.geometry("400x250")
        self.resizable(False, False)

        self.label = ctk.CTkLabel(self, text="Digite sua senha mestre:", font=("Arial", 14))
        self.label.pack(pady=30)

        self.entrada = ctk.CTkEntry(self, show="*", width=250)
        self.entrada.pack(pady=10)
        self.entrada.bind("<Return>", lambda event: self.tentar_login())

        self.botao = ctk.CTkButton(self, text="Entrar", command=self.tentar_login)
        self.botao.pack(pady=10)

        self.btn_criar = ctk.CTkButton(
            self, text="Criar senha mestre", command=self.criar_senha_mestre, width=200,
            fg_color="gray30", hover_color="gray40"
        )
        self.btn_criar.pack(pady=5)

        self.btn_recuperacao = ctk.CTkButton(
            self, text="Esqueci a senha mestre", command=self.abrir_recuperacao, width=200, fg_color="gray40", hover_color="gray30"
        )
        self.btn_recuperacao.pack(pady=5)

        self.senha_correta = None
        self.recuperacao_sucesso = None

        # Controle de tentativas e bloqueio por forca bruta
        self.tentativas_falhas = 0
        self.bloqueado_ate = None

    def tentar_login(self):
        # Verifica se esta bloqueado por forca bruta
        if self.bloqueado_ate is not None:
            if time.time() < self.bloqueado_ate:
                restante = int(self.bloqueado_ate - time.time())
                CTkMessageDialog(
                    "Bloqueado",
                    f"Muitas tentativas falhas. Tente novamente em {restante // 60} minuto(s).",
                    tipo="error",
                )
                return
            else:
                self.bloqueado_ate = None
                self.tentativas_falhas = 0

        senha = self.entrada.get()
        if not senha:
            CTkMessageDialog("Atencao", "Digite uma senha.", tipo="warning")
            return

        caminho_db = os.path.join(BASE_DIR, "data", "cofre.db")
        if not os.path.exists(caminho_db):
            if len(senha) < 8:
                CTkMessageDialog("Atencao", "A senha mestre deve ter pelo menos 8 caracteres.", tipo="warning")
                return
            banco = BancoSenhas(caminho_db, senha)
            recovery_key = gerar_chave_recuperacao()
            salvar_recovery(banco.fernet, recovery_key)
            salvar_recovery_visual(banco.fernet, recovery_key)
            banco.conexao.close()
            self.senha_correta = senha
            self.mostrar_chave_recuperacao(recovery_key)
            self.destroy()
        else:
            try:
                banco = BancoSenhas(caminho_db, senha)
                self.senha_correta = senha
                banco.conexao.close()
                self.destroy()
            except Exception:
                self.tentativas_falhas += 1
                if self.tentativas_falhas >= self.LIMITE_TENTATIVAS:
                    self.bloqueado_ate = time.time() + (self.TEMPO_BLOQUEIO_MS / 1000)
                    CTkMessageDialog(
                        "Bloqueado",
                        f"Muitas tentativas falhas. Tente novamente em {self.TEMPO_BLOQUEIO_MS // 60000} minuto(s).",
                        tipo="error",
                    )
                else:
                    CTkMessageDialog("Erro", "Senha mestre incorreta.", tipo="error")

    def criar_senha_mestre(self):
        """Cria a senha mestre na primeira execucao."""
        caminho_db = os.path.join(BASE_DIR, "data", "cofre.db")
        if os.path.exists(caminho_db):
            CTkMessageDialog(
                "Atencao",
                "Ja existe uma senha mestre. Use o botao Entrar para fazer login.",
                tipo="warning",
            )
            return

        senha = CTkInputDialog("Criar senha mestre", "Digite a nova senha mestre:").result
        if not senha:
            return
        if len(senha) < 8:
            CTkMessageDialog("Atencao", "A senha mestre deve ter pelo menos 8 caracteres.", tipo="warning")
            return

        confirma = CTkInputDialog("Criar senha mestre", "Confirme a senha mestre:").result
        if not confirma:
            return
        if senha != confirma:
            CTkMessageDialog("Erro", "As senhas nao coincidem.", tipo="error")
            return

        try:
            banco = BancoSenhas(caminho_db, senha)
            recovery_key = gerar_chave_recuperacao()
            salvar_recovery(banco.fernet, recovery_key)
            salvar_recovery_visual(banco.fernet, recovery_key)
            banco.conexao.close()
            self.senha_correta = senha
            self.mostrar_chave_recuperacao(recovery_key)
            self.destroy()
        except Exception as e:
            CTkMessageDialog("Erro", f"Nao foi possivel criar a senha mestre: {e}", tipo="error")

    def mostrar_chave_recuperacao(self, recovery_key):
        """Exibe a chave de recuperacao para o usuario anotar antes de prosseguir."""
        janela = ctk.CTkToplevel(self)
        janela.title("Chave de Recuperacao")
        janela.geometry("450x240")
        janela.resizable(False, False)

        ctk.CTkLabel(janela, text="ANOTE ESTA CHAVE EM PAPEL!", font=("Arial", 13, "bold"), text_color="orange").pack(pady=10)
        ctk.CTkLabel(janela, text="Sem ela, nao ha como recuperar sua senha mestre.", wraplength=400).pack(pady=5)

        frame_chave = ctk.CTkFrame(janela)
        frame_chave.pack(pady=10)
        txt_chave = ctk.CTkEntry(frame_chave, width=320, font=("Consolas", 14))
        txt_chave.insert(0, recovery_key)
        txt_chave.configure(state="readonly")
        txt_chave.pack(padx=10, pady=5)

        btn_ok = ctk.CTkButton(janela, text="Anotei e guardei em local seguro", command=janela.destroy)
        btn_ok.pack(pady=15)

        janela.transient(self)
        janela.grab_set()
        self.wait_window(janela)

    def abrir_recuperacao(self):
        self.withdraw()
        rec = TelaRecuperacao(self.master)
        self.master.wait_window(rec)
        if rec.sucesso:
            self.recuperacao_sucesso = rec.sucesso
            self.destroy()
        else:
            self.deiconify()


class TelaRecuperacao(ctk.CTkToplevel):
    """Tela para recuperar a senha mestre usando a chave de recuperacao."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Recuperar Senha Mestre")
        self.geometry("450x380")
        self.resizable(False, False)
        self.sucesso = None

        self.label = ctk.CTkLabel(self, text="Digite sua chave de recuperacao:", font=("Arial", 14))
        self.label.pack(pady=20)

        self.entrada_recovery = ctk.CTkEntry(self, width=300)
        self.entrada_recovery.pack(pady=10)

        self.btn_validar = ctk.CTkButton(self, text="Validar chave", command=self.validar_recovery)
        self.btn_validar.pack(pady=10)

        self.frame_nova = ctk.CTkFrame(self)
        self.frame_nova.pack(pady=10)
        self.frame_nova.pack_forget()

        ctk.CTkLabel(self.frame_nova, text="Nova senha mestre:").pack(pady=5)
        self.entrada_nova = ctk.CTkEntry(self.frame_nova, show="*", width=250)
        self.entrada_nova.pack(pady=5)

        ctk.CTkLabel(self.frame_nova, text="Confirmar nova senha:").pack(pady=5)
        self.entrada_confirma = ctk.CTkEntry(self.frame_nova, show="*", width=250)
        self.entrada_confirma.pack(pady=5)

        self.btn_redefinir = ctk.CTkButton(self.frame_nova, text="Redefinir senha", command=self.redefinir, fg_color="green", hover_color="darkgreen")
        self.btn_redefinir.pack(pady=15)

        self.btn_voltar = ctk.CTkButton(self, text="Voltar ao login", command=self.voltar, fg_color="gray40", hover_color="gray30")
        self.btn_voltar.pack(pady=10)

        self.chave_fernet_recuperada = None
        self.recovery_key_validada = ""

    def validar_recovery(self):
        recovery_key = self.entrada_recovery.get().strip()
        if not recovery_key:
            CTkMessageDialog("Atencao", "Digite a chave de recuperacao.", tipo="warning")
            return

        chave_fernet = tentar_recuperacao(recovery_key)
        if chave_fernet is None:
            CTkMessageDialog("Erro", "Chave de recuperacao invalida ou arquivo nao encontrado.", tipo="error")
            return

        self.chave_fernet_recuperada = chave_fernet
        self.recovery_key_validada = recovery_key
        self.entrada_recovery.configure(state="disabled")
        self.btn_validar.configure(state="disabled")
        self.frame_nova.pack(pady=10)
        CTkMessageDialog("Sucesso", "Chave validada. Digite agora a nova senha mestre.", tipo="info")

    def redefinir(self):
        nova = self.entrada_nova.get()
        confirma = self.entrada_confirma.get()
        if not nova or not confirma:
            CTkMessageDialog("Atencao", "Preencha ambos os campos.", tipo="warning")
            return
        if nova != confirma:
            CTkMessageDialog("Erro", "As senhas nao coincidem.", tipo="error")
            return
        if len(nova) < 8:
            CTkMessageDialog("Atencao", "A senha deve ter pelo menos 8 caracteres.", tipo="warning")
            return

        caminho_db = os.path.join(BASE_DIR, "data", "cofre.db")

        try:
            banco_antigo = BancoSenhas(caminho_db, chave_fernet_direta=self.chave_fernet_recuperada)
            senhas_antigas = banco_antigo.listar_todas()
            banco_antigo.conexao.close()

            os.remove(caminho_db)

            banco_novo = BancoSenhas(caminho_db, nova)
            for id_, servico, usuario, senha, excluida in senhas_antigas:
                if not excluida:
                    banco_novo.adicionar(servico, usuario, senha)

            salvar_recovery(banco_novo.fernet, self.recovery_key_validada)
            salvar_recovery_visual(banco_novo.fernet, self.recovery_key_validada)
            banco_novo.conexao.close()

            self.sucesso = nova
            self.destroy()
        except Exception as e:
            CTkMessageDialog("Erro", f"Nao foi possivel redefinir: {e}", tipo="error")

    def voltar(self):
        self.destroy()


class AppCofre(ctk.CTkToplevel):
    """Janela principal: lista, adiciona, exclui e gera senhas."""

    def __init__(self, master, chave_mestre):
        super().__init__(master)
        self.title("Coffre Digital - Minhas Senhas")
        self.geometry("700x500")

        # Armazena o handle da janela para restauracao via Win32 API
        self.update_idletasks()
        self._hwnd = self.winfo_id()

        self.banco = BancoSenhas(os.path.join(BASE_DIR, "data", "cofre.db"), chave_mestre)

        self.titulo = ctk.CTkLabel(self, text="Meu Cofre de Senhas", font=("Arial", 20, "bold"))
        self.titulo.pack(pady=15)

        self.frame_lista = ctk.CTkScrollableFrame(self, width=650, height=280)
        self.frame_lista.pack(pady=10)

        self.frame_botoes = ctk.CTkFrame(self)
        self.frame_botoes.pack(pady=10)

        self.btn_adicionar = ctk.CTkButton(
            self.frame_botoes, text="+ Adicionar", command=self.adicionar_senha, width=140
        )
        self.btn_adicionar.grid(row=0, column=0, padx=10)

        self.btn_gerar = ctk.CTkButton(
            self.frame_botoes, text="Gerar Senha", command=self.gerar_senha, width=140
        )
        self.btn_gerar.grid(row=0, column=1, padx=10)

        self.btn_reset = ctk.CTkButton(
            self.frame_botoes, text="Reset Total", command=self.reset_total, width=140, fg_color="red", hover_color="darkred", state="disabled"
        )
        self.btn_reset.grid(row=0, column=2, padx=10)

        self.btn_sair = ctk.CTkButton(
            self.frame_botoes, text="Sair", command=self.quit_app, width=100, fg_color="gray40"
        )
        self.btn_sair.grid(row=0, column=3, padx=10)

        self.btn_recuperacao_visual = ctk.CTkButton(
            self.frame_botoes, text="Ver Chave Recuperacao", command=self.mostrar_recuperacao_visual, width=180, fg_color="gray30", hover_color="gray40"
        )
        self.btn_recuperacao_visual.grid(row=1, column=0, columnspan=4, pady=8)

        self.carregar_lista()

        # ----------------------------
        # Bloqueio por inatividade
        # ----------------------------
        self.INATIVIDADE_LIMITE = 300000  # 5 minutos em milissegundos
        self._timer_inatividade = None
        self.bloqueado_por_inatividade = False

        # Rastreia qualquer tecla ou clique do mouse para resetar o timer
        self.bind("<Key>", self._resetar_inatividade)
        self.bind("<Button>", self._resetar_inatividade)
        self._monitorar_inatividade()

    def _resetar_inatividade(self, event=None):
        """Reseta o contador de inatividade ao detectar interacao do usuario."""
        if self._timer_inatividade:
            self.after_cancel(self._timer_inatividade)
        self._timer_inatividade = self.after(self.INATIVIDADE_LIMITE, self._bloquear_por_inatividade)

    def _monitorar_inatividade(self):
        """Inicia o monitoramento de inatividade (chamado uma vez no __init__)."""
        self._resetar_inatividade()

    def _bloquear_por_inatividade(self):
        """Bloqueia a sessao por inatividade e pede senha ao restaurar."""
        self.bloqueado_por_inatividade = True
        CTkMessageDialog(
            "Sessao bloqueada",
            "Nao houve atividade por 5 minutos. O cofre foi bloqueado por seguranca.\n"
            "Abra o programa novamente e digite sua senha mestre.",
            tipo="warning",
        )

    def _desbloquear_sessao(self):
        """Pede a senha mestre quando a sessao esta bloqueada por inatividade."""
        dialog = CTkInputDialog(
            "Desbloquear sessao",
            "Digite sua senha mestre:",
            show="*",
        )
        if dialog.result:
            try:
                BancoSenhas(
                    os.path.join(BASE_DIR, "data", "cofre.db"),
                    dialog.result,
                )
                self.bloqueado_por_inatividade = False
                self._resetar_inatividade()
            except Exception:
                pass
        else:
            pass

    # ----------------------------
    # Bandeja do sistema (tray)
    # ----------------------------
    def quit_app(self):
        """Fecha completamente o aplicativo (botao Sair da janela)."""
        liberar_mutex()
        self.destroy()

    def carregar_lista(self):
        """Limpa e reexibe todas as senhas salvas."""
        for widget in self.frame_lista.winfo_children():
            widget.destroy()

        try:
            senhas = self.banco.listar()
        except Exception as e:
            CTkMessageDialog("Erro", f"Nao foi possivel carregar: {e}", tipo="error")
            return

        if not senhas:
            vazio = ctk.CTkLabel(self.frame_lista, text="Nenhuma senha salva ainda.")
            vazio.pack(pady=20)
            self.btn_reset.configure(state="disabled")
            return

        self.btn_reset.configure(state="normal")

        for id_, servico, usuario, senha in senhas:
            linha = ctk.CTkFrame(self.frame_lista)
            linha.pack(fill="x", pady=5, padx=10)

            texto = f"{servico} | {usuario if usuario else '-'}"
            lbl = ctk.CTkLabel(linha, text=texto, anchor="w", width=300)
            lbl.pack(side="left", padx=10)

            btn_copiar = ctk.CTkButton(
                linha, text="Copiar", width=80,
                command=lambda s=senha: self.copiar(s)
            )
            btn_copiar.pack(side="right", padx=5)

            btn_apagar = ctk.CTkButton(
                linha, text="Excluir", width=80, fg_color="red", hover_color="darkred",
                command=lambda i=id_: self.excluir(i)
            )
            btn_apagar.pack(side="right", padx=5)

    def adicionar_senha(self):
        """Abre caixas de dialogo para cadastrar uma nova senha."""
        servico = CTkInputDialog("Novo cadastro", "Servico (ex: Gmail, Netflix):").result
        if not servico:
            return
        usuario = (CTkInputDialog("Novo cadastro", "Usuario / e-mail (opcional):").result) or ""
        senha = CTkInputDialog("Novo cadastro", "Senha:", show="*").result
        if not senha:
            return

        try:
            self.banco.adicionar(servico, usuario, senha)
            self.carregar_lista()
            CTkMessageDialog("Sucesso", "Senha salva com sucesso!", tipo="info")
        except Exception as e:
            CTkMessageDialog("Erro", f"Nao foi possivel salvar: {e}", tipo="error")

    def gerar_senha(self):
        """Gera uma senha aleatoria e salva no cofre com servico e usuario informados."""
        servico = CTkInputDialog("Gerar senha", "Servico (ex: Gmail, Netflix):").result
        if not servico:
            return
        usuario = (CTkInputDialog("Gerar senha", "Usuario / e-mail (opcional):").result) or ""

        tamanho = 12
        caracteres = string.ascii_letters + string.digits + "!@#$%&*"
        senha = ''.join(random.choice(caracteres) for _ in range(tamanho))

        try:
            self.banco.adicionar(servico, usuario, senha)
            self.carregar_lista()
            self.clipboard_clear()
            self.clipboard_append(senha)
            CTkMessageDialog("Senha gerada", f"Senha gerada para {servico}:\n\nSenha: {senha}\n\nEla foi copiada para a área de transferência e salva no cofre.", tipo="info")
            # Limpa a area de transferencia apos 30 segundos por seguranca
            self.after(30000, self.clipboard_clear)
        except Exception as e:
            CTkMessageDialog("Erro", f"Nao foi possivel salvar: {e}", tipo="error")

    def copiar(self, senha):
        """Copia a senha para a area de transferencia."""
        self.clipboard_clear()
        self.clipboard_append(senha)
        CTkMessageDialog("Copiado", "Senha copiada para a area de transferencia.", tipo="info")
        # Limpa a area de transferencia apos 30 segundos por seguranca
        self.after(30000, self.clipboard_clear)

    def excluir(self, id_):
        """Confirma e exclui uma senha."""
        confirmar = CTkConfirmDialog("Excluir", "Tem certeza que deseja apagar esta senha?").result
        if confirmar:
            try:
                self.banco.excluir(id_)
                self.carregar_lista()
                CTkMessageDialog("Sucesso", "Senha excluida.", tipo="info")
            except Exception as e:
                CTkMessageDialog("Erro", f"Nao foi possivel excluir: {e}", tipo="error")

    def reset_total(self):
        """Apaga todas as senhas apos confirmacao e validacao da senha mestre."""
        confirmar = CTkConfirmDialog(
            "Reset Total",
            "TEM CERTEZA? Isso apaga TODAS as senhas do cofre de forma irreversível.",
        ).result
        if not confirmar:
            return

        senha = CTkInputDialog("Reset Total", "Digite sua senha mestre para confirmar:", show="*").result
        if not senha:
            return

        try:
            teste = BancoSenhas(os.path.join(BASE_DIR, "data", "cofre.db"), senha)
        except Exception:
            CTkMessageDialog("Erro", "Senha mestre incorreta. Cancelando reset.", tipo="error")
            return

        try:
            cursor = self.banco.conexao.cursor()
            cursor.execute("DELETE FROM senhas")
            self.banco.conexao.commit()
            self.carregar_lista()
            CTkMessageDialog("Reset Total", "Todas as senhas foram apagadas de forma irreversivel.", tipo="info")
        except Exception as e:
            CTkMessageDialog("Erro", f"Nao foi possivel resetar: {e}", tipo="error")

    def mostrar_recuperacao_visual(self):
        """Exibe a chave de recuperacao armazenada (descriptografada com a senha mestre atual)."""
        recovery_key = carregar_recovery_visual(self.banco.fernet)

        if not recovery_key:
            # Nao existe arquivo de visualizacao (banco antigo ou arquivo ausente).
            # Gera uma nova chave de recuperacao e salva para visualizacao futura.
            try:
                recovery_key = gerar_chave_recuperacao()
                salvar_recovery(self.banco.fernet, recovery_key)
                salvar_recovery_visual(self.banco.fernet, recovery_key)
                CTkMessageDialog("Nova Chave Gerada", "Uma nova Chave de Recuperacao foi gerada e salva.\nAnote-a em local seguro!", tipo="info")
            except Exception as e:
                CTkMessageDialog("Erro", f"Nao foi possivel gerar a chave de recuperacao: {e}", tipo="error")
                return

        janela = ctk.CTkToplevel(self)
        janela.title("Chave de Recuperacao")
        janela.geometry("450x220")
        janela.resizable(False, False)

        ctk.CTkLabel(janela, text="Sua Chave de Recuperacao:", font=("Arial", 13, "bold")).pack(pady=10)
        ctk.CTkLabel(janela, text="Guarde essa chave em local seguro.", wraplength=400).pack(pady=5)

        frame_chave = ctk.CTkFrame(janela)
        frame_chave.pack(pady=10)
        txt_chave = ctk.CTkEntry(frame_chave, width=320, font=("Consolas", 14))
        txt_chave.insert(0, recovery_key)
        txt_chave.configure(state="readonly")
        txt_chave.pack(padx=10, pady=5)

        frame_botoes = ctk.CTkFrame(janela, fg_color="transparent")
        frame_botoes.pack(pady=15)

        btn_copiar = ctk.CTkButton(
            frame_botoes, text="Copiar Chave", command=lambda: self._copiar_texto(recovery_key),
            width=120, fg_color="gray30", hover_color="gray40"
        )
        btn_copiar.pack(side="left", padx=10)

        btn_ok = ctk.CTkButton(frame_botoes, text="OK", command=janela.destroy, width=100)
        btn_ok.pack(side="left", padx=10)

        janela.transient(self)
        janela.grab_set()
        self.wait_window(janela)

    def _copiar_texto(self, texto):
        """Copia texto para a area de transferencia."""
        self.clipboard_clear()
        self.clipboard_append(texto)
        CTkMessageDialog("Copiado", "Chave de recuperacao copiada para a area de transferencia.", tipo="info")
        # Limpa a area de transferencia apos 30 segundos por seguranca
        self.after(30000, self.clipboard_clear)

if __name__ == "__main__":
    if outra_instancia_rodando():
        if not restaurar_janela_existente():
            CTkMessageDialog("Coffre Digital", "O programa ja esta em execucao.", tipo="warning")
        liberar_mutex()
        sys.exit(0)

    raiz = ctk.CTk()
    # Esconde a raiz (janela principal do tkinter) - usamos apenas Toplevels
    raiz.withdraw()

    try:
        login = TelaLogin(raiz)
        raiz.wait_window(login)

        if login.senha_correta:
            app = AppCofre(raiz, login.senha_correta)
            raiz.wait_window(app)
        elif login.recuperacao_sucesso:
            app = AppCofre(raiz, login.recuperacao_sucesso)
            raiz.wait_window(app)
    finally:
        liberar_mutex()
        raiz.destroy()