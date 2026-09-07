// @nsfocus/nf-brand —— 服务端（node）半体。
// 纯品牌呈现类插件：没有服务端行为，node 半边只需一个空 apply 构成 Loader seat，
// 浏览器半边经 package.json 的 exports["./client"] 由 dsh web 自动构建并 /plugins 下发。
export function apply() {}