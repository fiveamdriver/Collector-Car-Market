import Foundation
import PDFKit
// usage: pdftext <in.pdf> <out.json>  -> JSON array of page strings
let args = CommandLine.arguments
guard args.count == 3, let doc = PDFDocument(url: URL(fileURLWithPath: args[1])) else {
    FileHandle.standardError.write("cannot open pdf\n".data(using: .utf8)!); exit(1)
}
var pages: [String] = []
for i in 0..<doc.pageCount { pages.append(doc.page(at: i)?.string ?? "") }
let data = try JSONSerialization.data(withJSONObject: pages)
try data.write(to: URL(fileURLWithPath: args[2]))
print("pages:", doc.pageCount, "with text:", pages.filter { $0.count > 50 }.count)
