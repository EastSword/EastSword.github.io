#!/usr/bin/env ruby
# 本地编辑器预览渲染：与 GitHub Pages 同引擎（kramdown + GFM 输入）
# stdin 读 markdown，stdout 输出 HTML
require "kramdown"
require "kramdown-parser-gfm"

input = STDIN.read.force_encoding("UTF-8")
print Kramdown::Document.new(input, input: "GFM").to_html
