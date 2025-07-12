# 2B - Sua Assistente Pessoal

2B é uma assistente de linha de comando desenvolvida em Python para te ajudar com diversas tarefas, desde executar ações complexas no terminal, pesquisar na web e sintetizar informações, até explicar comandos, gerar código e gerenciar lembretes. Ela é personalizável e projetada para ser sua parceira tecnológica definitiva.

## ✅ Pré-requisitos

- **Python 3.6+**
  Certifique-se de ter o Python 3 instalado no seu sistema.

- **Chave da API Google (Gemini)**
  Você precisará de uma chave da API do Google para o modelo Gemini.
  
  👉 Obtenha a sua em: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

- **Dependências Python**
  - `genai-google`: Para se comunicar com a API do Gemini.
  - `rich`: Para uma saída de terminal mais bonita e interativa.
  - `requests`: Para o módulo de busca na web.
  - `beautifulsoup4`: Para extrair conteúdo das páginas web na busca.
  - `keyring`: Para armazenar a API Key no cofre do aparelho.
  - `tiktoken`: Para contagem precisa de tokens.
  - `lxml`: (Opcional, mas recomendado) Um parser de HTML mais rápido para a busca.
  - **Para usuários do Termux:**
    - `at`: Para agendamento de tarefas em segundo plano (notificações).
    - `termux-services`: Para gerenciar o serviço `atd`.

---

## ⚙️ Instalação e Configuração

Siga estes passos para ter a 2B pronta para uso na sua máquina.

### 1. Clone o Repositório
Primeiro, clone o projeto para sua máquina e entre no diretório criado.

```bash
git clone https://github.com/Nekyl/2ByNekyl.git
cd 2ByNekyl
```

### 2. Instale as Dependências

Use o arquivo `requirements.txt` para instalar todas as bibliotecas Python necessárias:

```bash
pip install --upgrade -r requirements.txt
```
> **Observação:** Se a instalação do `keyring` falhar, não se preocupe! A 2B entrará em um modo de emergência para te ajudar a consertar a própria instalação.

No **Termux**, instale também os pacotes adicionais:

```bash
pkg install at termux-services
```

Além disso, instale o aplicativo **Termux:API**  
(Recomendado via [F-Droid](https://f-droid.org/packages/com.termux.api/)).


### 3. Torne o Script Executável

```bash
chmod +x 2b.py
```

### 4. Configure a Chave da API e Usuário

#### Método Padrão (Seguro)
Este é o método recomendado. A 2B usará a biblioteca `keyring` para guardar sua chave no cofre de senhas do seu sistema operacional.

```bash
./2b.py config api_key
# Ela vai pedir pra você inserir de forma segura, e a digitação ficará oculta.
```

> #### ⚠️ Modo de Emergência (Se a instalação do `keyring` falhar)
> Se você teve problemas para instalar a biblioteca `keyring`, pode usar o seguinte comando para uma **configuração temporária e insegura**:
> ```bash
> ./2b.py config api_key SUA_CHAVE_AQUI
> ```
> Ao fazer isso, a 2B salvará sua chave em um arquivo de configuração e, em seguida, **se oferecerá para iniciar o modo agente para te ajudar a instalar o `keyring` corretamente**. Assim que a instalação for bem-sucedida, a 2B moverá automaticamente sua chave para o cofre seguro na próxima vez que for executada.

#### Configurando seu Nome
Me diga como você gostaria de ser chamado. ❤️

```bash
./2b.py config user SeuNome  
```


### 5. (Opcional) Configure a Personalidade

```bash
./2b.py config personality neutra
# Usando './2b.py config' visualize as opções disponíveis 
```

### 6. (Opcional) Configurar alias e saudação
Podemos configurar um alias para chamar 2B de qualquer diretório e também uma saudação com lembrete de eventos sempre que iniciar o terminal. Usando seu editor de texto favorito, edite o `~/.bashrc` ou `~/.zshrc` e adicione as seguintes linhas:

```bash
# Saudação sempre que iniciar o terminal (mostra lembretes se houver)
~/2ByNekyl/2b.py hi

# Atalho para chamar 2B e passar parâmetros em qualquer diretório 
alias 2b='~/2ByNekyl/2b.py'
```
> Lembre-se de reiniciar seu terminal ou rodar `source ~/.bashrc` para aplicar as mudanças.

### 7. (Para Termux) Habilitando o Serviço `atd`
Para que os lembretes agendados funcionem corretamente em segundo plano, o serviço **`atd`** precisa estar ativo.

1.  **Ative o serviço `atd`:**
    ```bash
    sv-enable atd
    ```
    > ⚠️ Após executar esse comando, **reinicie o Termux**.

2.  **Inicie o serviço manualmente (apenas uma vez):**
    Após reiniciar o Termux, rode:
    ```bash
    sv up atd
    ```
    Isso garante que o serviço estará rodando ativamente.

**Verificações adicionais:** Desative a otimização de bateria para os apps `Termux` e `Termux:API` e conceda as permissões de notificação e de aparecer sobre outros apps.

---

## 🚀 Modo Inteligente (Dispatcher)

Para facilitar o uso, a 2B possui um "dispatcher" inteligente. Se você não especificar um comando (`do`, `search`, etc.), ela analisará sua solicitação e escolherá a melhor ferramenta para o trabalho automaticamente.

**Uso:**

```bash
2b "[sua solicitação em linguagem natural]"
```

**Exemplos:**

*   Ela entenderá que é para adicionar um lembrete:
    ```bash
    2b "lembre-me de comprar pão amanhã às 10h"
    ```
*   Ela saberá que precisa usar a ferramenta de busca:
    ```bash
    2b "qual a capital da Austrália?"
    ```
*   Ela iniciará uma conversa:
    ```bash
    2b "bom dia, como você está?"
    ```

## Comandos Disponíveis

A 2B oferece os seguintes comandos explícitos:

### `do` (ou `d`)

Executa tarefas complexas no terminal de forma sequencial e interativa. A 2B age como um agente autônomo, planejando, pesquisando, executando comandos e pedindo sua permissão quando necessário.

**Uso:**

```bash
2b do "[sua tarefa complexa]"
```

**Exemplos:**

*   Instalar uma ferramenta e configurar um projeto:
    ```bash
    2b do "verificar se o docker está instalado, se não estiver, me pergunte se quero instalar. Depois, baixe a imagem do nginx e rode um container na porta 8080"
    ```

*   Gerenciar processos:
    ```bash
    2b d "liste os processos rodando na porta 3000 e finalize o processo encontrado"
    ```

### `search` (ou `s`)

Pesquisa um tópico na web, lê as melhores fontes, e sintetiza uma resposta completa e coesa, citando as fontes utilizadas.

**Uso:**

```bash
2b search "[o que você quer pesquisar]"
```

**Exemplos:**

*   Pesquisar um tópico técnico:
    ```bash
    2b search "diferenças entre os modelos gemini 1.5 pro e flash"
    ```

*   Buscar opiniões ou comparações:
    ```bash
    2b s qual a melhor biblioteca python para web scraping em 2025
    # search, do e dispatcher não precisam de aspas
    ```

### `explain` (ou `ex`)

Explica comandos de terminal, trechos de código, scripts ou mensagens de erro. Pode ser usado com uma query direta ou lendo de um arquivo.

**Uso:**

```bash
2b explain "[sua query]"
2b ex -f [caminho/para/seu/arquivo]
```

**Exemplos:**

*   Explicar um comando do Git:
    ```bash
    2b explain "git rebase -i HEAD~3"
    ```

*   Analisar um script e fazer uma pergunta:
    ```bash
    2b ex "Qual o propósito principal deste script?" -f ./meu_script_complexo.sh
    ```

### `generate` (ou `gen`)

Gera scripts, trechos de código ou arquivos de configuração com base em uma descrição.

**Uso:**

```bash
2b generate "[o que você quer gerar]" [-l linguagem] [-i arquivo_de_entrada] [-o arquivo_de_saida]
```

**Argumentos:**
*   `--lang` ou `-l`: Sugere a linguagem (ex: `python`, `bash`).
*   `--input-file` ou `-i`: Usa um arquivo como contexto.
*   `--output` ou `-o`: Salva a saída em um arquivo.

**Exemplos:**

*   Gerar um script Python e salvá-lo:
    ```bash
    2b gen "script python que renomeia todos os arquivos .jpg para .jpeg em uma pasta" -l python -o rename.py
    ```

*   Gerar um Dockerfile a partir de um contexto:
    ```bash
    2b gen "crie um Dockerfile para esta aplicação" -i main.py -o Dockerfile
    ```

### `chat` (ou `c`)

Inicia uma conversa interativa com a 2B ou envia uma única mensagem. A 2B usará o histórico da conversa para manter o contexto.

**Uso:**

```bash
2b chat "[sua mensagem]"
2b c
```
*   Se você executar `chat` sem argumentos, ele iniciará um **modo interativo**. Digite `sair` ou `exit` para terminar.

### `remember` (ou `rem`)

Gerencia seus lembretes. A 2B tenta parsear data/hora da sua descrição para agendar notificações.

**Subcomandos:**

*   `add "[texto]"`: Adiciona um lembrete.
    ```bash
    2b rem add "Reunião de equipe amanhã às 14h30"
    ```

*   `ls [--all]`: Lista lembretes. `--all` inclui os concluídos.
    ```bash
    2b rem ls
    ```
*   `done [ID]`: Marca um lembrete como concluído.
    ```bash
    2b rem done 3
    ```

*   `rm [ID|all|done]`: Remove lembretes.
    - `[ID]`: Remove um lembrete específico.
    - `all`: Remove TODOS os lembretes.
    - `done`: Remove apenas os lembretes concluídos.
    ```bash
    2b rem rm done
    ```

### `greet` (ou `hi`)
Exibe uma saudação amigável, ideal para usar no seu arquivo de inicialização do shell (`.bashrc` ou `.zshrc`).

**Uso:**
```bash
2b greet
```

### `config`

Configura as opções da 2B, como a chave da API, nome de usuário e a personalidade.

**Uso:**

```bash
2b config [chave] [valor]
```

**Exemplos:**

*   Configurar a chave da API:
    ```bash
    2b config api_key SUA_CHAVE_API  
    ```
*   Configurar seu nome:
    ```bash
    2b config user SeuNome
    ```
*   Mudar a personalidade:
    ```bash
    2b config personality hacker
    ```
*   Ver a configuração atual (sem argumentos):
    ```bash
    2b config
    ```

---

## 🧠 Personalidades da 2B

A 2B pode assumir diferentes personalidades. Configure com `2b config personality [nome]`.

*   **`fofa`**: Doce e prestativa, usa emojis e um tom afetuoso.
*   **`hacker`**: Direta, prática e um pouco rebelde, resolve problemas com eficiência e gírias de hacking.
*   **`neutra`**: Objetiva, profissional e leal, oferece informações claras e confiáveis.

Use `2b config` para ver as opções disponíveis e escolha a que mais te agrada! 😉

_2ByNekyll-1.1.1_
