function escapeHtml(source) {
  return source
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

export function highlightJava(source) {
  if (!source) {
    return ''
  }

  // 先转义 HTML，再按顺序匹配（多行注释 → 单行注释 → 字符串 → 关键字 → 类型 → 数字）
  return escapeHtml(source)
    .replace(/(\/\*[\s\S]*?\*\/)/g, '<span class="token-comment">$1</span>')
    .replace(/(\/\/[^\n]*)/g, '<span class="token-comment">$1</span>')
    .replace(/("(?:[^"\\]|\\.)*")/g, '<span class="token-string">$1</span>')
    .replace(/\b(public|private|protected|class|interface|enum|abstract|final|static|void|new|return|if|else|for|while|do|switch|case|break|continue|default|try|catch|finally|throw|throws|package|import|extends|implements|instanceof|synchronized|transient|volatile|native|strictfp|assert|this|super|true|false|null)\b/g, '<span class="token-keyword">$1</span>')
    .replace(/\b(String|Integer|Double|Boolean|Long|Float|Short|Byte|Character|int|long|double|boolean|float|short|byte|char|Object|ArrayList|LinkedList|HashMap|HashSet|List|Map|Set|Collection|Optional|System|Math|Arrays|Collections|StringBuilder|StringBuffer|Thread|Exception|RuntimeException|Void)\b/g, '<span class="token-type">$1</span>')
    .replace(/\b(\d+\.?\d*[fFdDlL]?)\b/g, '<span class="token-number">$1</span>')
}

export function highlightCangjie(source) {
  if (!source) {
    return ''
  }

  return escapeHtml(source)
    .replace(/(\/\*[\s\S]*?\*\/)/g, '<span class="token-comment">$1</span>')
    .replace(/(\/\/[^\n]*)/g, '<span class="token-comment">$1</span>')
    .replace(/("(?:[^"\\]|\\.)*")/g, '<span class="token-string">$1</span>')
    .replace(/\b(package|import|main|class|interface|struct|enum|extend|func|init|operator|let|var|const|if|else|for|while|do|match|return|break|continue|throw|try|catch|finally|true|false|null|this|super|new|is|as|in|where|open|abstract|override|public|private|protected|internal|static|sealed|unsafe|spawn|async|await|mut)\b/g, '<span class="token-keyword">$1</span>')
    .replace(/\b(Int8|Int16|Int32|Int64|Int|UInt8|UInt16|UInt32|UInt64|UInt|Float16|Float32|Float64|Float|Double|Bool|String|Char|Byte|Rune|Unit|Nothing|Array|ArrayList|HashMap|HashSet|Option|Result|Tuple)\b/g, '<span class="token-type">$1</span>')
    .replace(/\b(\d+\.?\d*[fFdDlL]?)\b/g, '<span class="token-number">$1</span>')
}