function escapeHtml(source) {
  return source
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

// 用占位符临时保护已生成的 span，防止后续 regex 误匹配 HTML 属性中的关键字
function protect(text, placeholders, regex, wrapper) {
  return text.replace(regex, (match) => {
    const idx = placeholders.length
    placeholders.push(wrapper(match))
    return `\x00PLACEHOLDER_${idx}\x00`
  })
}

function restore(text, placeholders) {
  return text.replace(/\x00PLACEHOLDER_(\d+)\x00/g, (_, i) => placeholders[Number(i)])
}

export function highlightJava(source) {
  if (!source) {
    return ''
  }

  const placeholders = []
  let text = escapeHtml(source)

  // 先保护注释和字符串（占位符化），避免后续 regex 误匹配其内部内容
  text = protect(text, placeholders, /(\/\*[\s\S]*?\*\/)/g,
    m => `<span class="token-comment">${m}</span>`)
  text = protect(text, placeholders, /(\/\/[^\n]*)/g,
    m => `<span class="token-comment">${m}</span>`)
  text = protect(text, placeholders, /("(?:[^"\\]|\\.)*")/g,
    m => `<span class="token-string">${m}</span>`)

  // 关键字、类型、数字只作用于普通文本
  text = text.replace(/\b(public|private|protected|class|interface|enum|abstract|final|static|void|new|return|if|else|for|while|do|switch|case|break|continue|default|try|catch|finally|throw|throws|package|import|extends|implements|instanceof|synchronized|transient|volatile|native|strictfp|assert|this|super|true|false|null)\b/g,
    '<span class="token-keyword">$1</span>')
  text = text.replace(/\b(String|Integer|Double|Boolean|Long|Float|Short|Byte|Character|int|long|double|boolean|float|short|byte|char|Object|ArrayList|LinkedList|HashMap|HashSet|List|Map|Set|Collection|Optional|System|Math|Arrays|Collections|StringBuilder|StringBuffer|Thread|Exception|RuntimeException|Void)\b/g,
    '<span class="token-type">$1</span>')
  text = text.replace(/\b(\d+\.?\d*[fFdDlL]?)\b/g,
    '<span class="token-number">$1</span>')

  return restore(text, placeholders)
}

export function highlightCangjie(source) {
  if (!source) {
    return ''
  }

  const placeholders = []
  let text = escapeHtml(source)

  text = protect(text, placeholders, /(\/\*[\s\S]*?\*\/)/g,
    m => `<span class="token-comment">${m}</span>`)
  text = protect(text, placeholders, /(\/\/[^\n]*)/g,
    m => `<span class="token-comment">${m}</span>`)
  text = protect(text, placeholders, /("(?:[^"\\]|\\.)*")/g,
    m => `<span class="token-string">${m}</span>`)

  text = text.replace(/\b(package|import|main|class|interface|struct|enum|extend|func|init|operator|let|var|const|if|else|for|while|do|match|return|break|continue|throw|try|catch|finally|true|false|null|this|super|new|is|as|in|where|open|abstract|override|public|private|protected|internal|static|sealed|unsafe|spawn|async|await|mut)\b/g,
    '<span class="token-keyword">$1</span>')
  text = text.replace(/\b(Int8|Int16|Int32|Int64|Int|UInt8|UInt16|UInt32|UInt64|UInt|Float16|Float32|Float64|Float|Double|Bool|String|Char|Byte|Rune|Unit|Nothing|Array|ArrayList|HashMap|HashSet|Option|Result|Tuple)\b/g,
    '<span class="token-type">$1</span>')
  text = text.replace(/\b(\d+\.?\d*[fFdDlL]?)\b/g,
    '<span class="token-number">$1</span>')

  return restore(text, placeholders)
}
