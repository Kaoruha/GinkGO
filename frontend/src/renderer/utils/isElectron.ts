// 双形态判定:Electron 形态下 preload 注入 window.appConfig.isElectron=true
// 浏览器形态下 window.appConfig 为 undefined(或 isElectron 字段缺失)→ false
// 模块加载时捕获一次,后续稳定(Tasks 7-8 之间契约)
export const isElectron = !!window.appConfig?.isElectron
