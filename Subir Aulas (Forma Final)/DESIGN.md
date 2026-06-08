# DONA FRANCISCA - DESIGN SYSTEM SPECIFICATION (Stitch Format)

Esta especificação visual documenta os tokens visuais e padrões de interface do aplicativo desktop **Dona Francisca** (migração de módulos). Ela serve para alinhar o estilo estético e garantir que qualquer geração futura de interface por IA siga os mesmos critérios visuais premium.

---

## 1. Cores e Tokens Visuais

### Tema Escuro (Padrão)
| Token | Cor Hex | Uso Prático |
| :--- | :---: | :--- |
| `BG_WINDOW` | `#0D131A` | Fundo principal da janela principal e secundárias. |
| `BG_CARD` | `#131B26` | Fundo de painéis agrupadores, cards e tabelas. |
| `BG_INPUT` | `#0B0F14` | Fundo de inputs (`CTkEntry`), textboxes (`CTkTextbox`) e campos de formulário. |
| `BORDER_COLOR` | `#1E293B` | Bordas finas de 1px em cards e separadores visuais. |
| `TEXT_LIGHT` | `#F1F5F9` | Cor primária para títulos e textos importantes. |
| `TEXT_MUTED` | `#94A3B8` | Cor secundária para descrições, labels de formulários e status inativos. |

### Tema Claro
| Token | Cor Hex | Uso Prático |
| :--- | :---: | :--- |
| `BG_WINDOW` | `#F1F5F9` | Fundo principal da janela. |
| `BG_CARD` | `#FFFFFF` | Fundo de painéis e cards. |
| `BG_INPUT` | `#F8FAFC` | Fundo de inputs e textboxes. |
| `BORDER_COLOR` | `#E2E8F0` | Bordas e divisores visuais. |
| `TEXT_LIGHT` | `#1E293B` | Texto principal no modo claro. |
| `TEXT_MUTED` | `#64748B` | Texto secundário no modo claro. |

### Cores Semânticas de Ação
* **Ação Principal / Sucesso (Verde):** `#10B981` (`VERDE_ACAO` / `color_green`) | Hover: `#059669` (`VERDE_HOVER`)
* **Destaques / Info (Ciano):** `#00F2FE` (`color_cyan`)
* **Parada / Erro (Vermelho):** `#EF4444` (`VERMELHO_PARAR` / `color_red`)
* **Alerta / Pendente (Amarelo):** `#F59E0B` (`color_yellow`)
* **Assistente IA (Roxo):** `#8B5CF6` (`ROXO_IA`)

---

## 2. Tipografia

Usamos uma hierarquia visual moderna com as seguintes famílias de fontes padrão (fontes nativas do Windows ou instaladas):

* **Títulos Principais e Destaques:** `Space Grotesk` (ex: `("Space Grotesk", 16, "bold")`)
* **Textos de Corpo, Descrições e Rótulos:** `Inter` (ex: `("Inter", 12)`, `("Inter", 9, "bold")`)
* **Console e Saída de Logs:** `Consolas` (ex: `("Consolas", 12)`)

---

## 3. Geometria e Layout

* **Janelas Secundárias (`CTkToplevel`):** 
  * Devem usar cantos padrão e ser centralizadas ou ter dimensões fixas (ex: `500x750` para Configurações, `900x600` para Histórico BD).
  * Sempre usar o atributo `attributes("-topmost", True)` para evitar que fiquem ocultas atrás do navegador ou janela principal.
* **Margens e Paddings:**
  * Margem externa dos containers principais: `padx=20`, `pady=20` ou `padx=15`, `pady=15`.
  * Margem interna entre elementos: `pady=6`, `padx=6`.
  * Altura padrão para botões de navegação e inputs: `height=36` ou `40`.
  * Altura para botões de ação críticos (migrar, salvar, parar): `height=45` ou `48` com cantos mais arredondados (`corner_radius=12`).
  * Cantos arredondados padrão:
    * Cards e Frames agrupadores: `corner_radius=12`.
    * Inputs e Botões comuns: `corner_radius=8` ou `6`.
