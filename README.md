# YouTube Watch Later

Aplicação Python que abre a playlist **Assistir mais tarde** do YouTube no
Brave, coleta os vídeos carregados e exporta os dados para um arquivo CSV.

## Requisitos

- Python 3.10 ou superior;
- Brave Browser instalado;
- Selenium 4;
- pytest 8;
- sessão do YouTube disponível no perfil do Brave usado pela aplicação.

O Selenium Manager tenta localizar ou obter automaticamente o driver
compatível com o navegador.

## Instalação

Crie e ative um ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instale as dependências:

```powershell
pip install -r requirements.txt
```

## Configuração

Por padrão, a aplicação usa o perfil `Default` do Brave e estes diretórios:

- Windows: `%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data`;
- outros sistemas: `~/.config/brave`.

No Windows, o executável é esperado em:

```text
C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe
```

Se o Brave estiver instalado em outro local, ajuste `create_driver()` em
`src/web_driver.py` antes de executar a aplicação.

## Execução

Com o ambiente virtual ativo:

```powershell
python main.py
```

O navegador será aberto na playlist `https://www.youtube.com/playlist?list=WL`.
Se necessário, faça login na janela aberta. A aplicação aguarda os vídeos,
rola a página para carregar os lotes seguintes e encerra o navegador ao final.

## Saída

O arquivo gerado é:

```text
output/watch_later.csv
```

Ele contém as colunas:

| Coluna | Descrição |
| --- | --- |
| `title` | Título do vídeo |
| `url` | URL do vídeo |
| `duration` | Duração encontrada |
| `channel` | Canal do vídeo |

O CSV é salvo em UTF-8 com BOM para facilitar a abertura no Excel.

## Arquitetura

- `main.py`: coordena a execução da aplicação.
- `src/web_driver.py`: configura o Brave, aguarda a playlist, rola a página
  e extrai os vídeos em lotes.
- `src/video.py`: define o modelo imutável `Video`.
- `src/file_writer.py`: grava os vídeos no CSV.
- `tests/`: testes unitários de parsing, normalização, deduplicação e
  extração em lote.

A coleta processa cada lote novo uma única vez e usa a URL como chave de
deduplicação. A leitura dos campos de um lote é feita por uma chamada
JavaScript, reduzindo as chamadas individuais ao Selenium.

## Testes

Execute os testes sem abrir o navegador:

```powershell
pytest -q
```

Para verificar a compilação dos módulos:

```powershell
python -m compileall -q main.py src tests
```

## Observações

- O YouTube pode alterar a estrutura HTML e os seletores usados pelo scraper.
- A playlist precisa estar acessível pela conta autenticada no perfil do
  Brave configurado.
- O arquivo em `output/` é gerado localmente e não faz parte do código-fonte.
