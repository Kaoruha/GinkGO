/**
 * 复制文本到剪贴板。
 * navigator.clipboard 仅安全上下文(https/localhost)可用;局域网 http 部署(如
 * http://192.168.x.x:5173)下为 undefined,须降级 execCommand——否则"点击复制"
 * 永远走失败分支,只能弹 ID 文本提示。
 */
export async function copyText(text: string): Promise<boolean> {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // 权限拒绝等,继续走降级
    }
  }
  // 降级:临时 textarea + execCommand(需在用户激活窗口内,click 处理器中调用)
  const ta = document.createElement('textarea')
  ta.value = text
  ta.style.position = 'fixed'
  ta.style.opacity = '0'
  document.body.appendChild(ta)
  ta.select()
  let ok: boolean
  try {
    ok = document.execCommand('copy')
  } catch {
    ok = false
  }
  document.body.removeChild(ta)
  return ok
}
