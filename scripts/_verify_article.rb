require "kramdown"
require "kramdown-parser-gfm"

text = File.read("_articles/llm-api-key-leak.md", encoding: "utf-8")
body = text.split("---", 2)[1].split("---", 2)[1]
html = Kramdown::Document.new(body, input: "GFM").to_html
File.write("/tmp/article_gfm.html", html)

h2 = html.scan(/<h2 id="([^"]*)"/).flatten
h3 = html.scan(/<h3 id="([^"]*)"/).flatten
puts "h2: #{h2.size} 章，id 全部 ch 前缀: #{h2.all? { |i| i.start_with?("ch") }}"
puts "h3: #{h3.size} 节，id 全部 ch 前缀: #{h3.all? { |i| i.start_with?("ch") }}"
puts "代码块: #{html.scan(/<pre/).size} 个"
puts "表格: #{html.scan(/<table>/).size} 个"
puts "图片: #{html.scan(/<img/).size} 张"
puts "外链: #{html.scan(/<a href="https?:/).size} 个"
puts "字面量 {: 残留: " + (html.include?("{:") ? "有! " + html[/[^>]*\{:[^<]*/].to_s[0,100] : "无")
