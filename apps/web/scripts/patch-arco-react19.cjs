const fs = require("fs");
const path = require("path");

const arcoRoot = path.dirname(
  require.resolve("@arco-design/web-react/package.json")
);

const patches = [
  {
    file: "es/_util/react-dom.js",
    search: "if (children && children.ref) {\n        if (isFunction(children.ref)) {\n            children === null || children === void 0 ? void 0 : children.ref(node);\n        }\n        if ('current' in children.ref) {\n            children.ref.current = node;\n        }\n    }",
    replace: "var _a;\n    if (children && ((_a = children.props) === null || _a === void 0 ? void 0 : _a.ref)) {\n        var ref = children.props.ref;\n        if (isFunction(ref)) {\n            ref(node);\n        }\n        if ('current' in ref) {\n            ref.current = node;\n        }\n    }\n    else if (children && children.ref) {\n        if (isFunction(children.ref)) {\n            children === null || children === void 0 ? void 0 : children.ref(node);\n        }\n        if ('current' in children.ref) {\n            children.ref.current = node;\n        }\n    }",
  },
  {
    file: "lib/_util/react-dom.js",
    search: "if (children && children.ref) {\n        if ((0, is_1.isFunction)(children.ref)) {\n            children === null || children === void 0 ? void 0 : children.ref(node);\n        }\n        if ('current' in children.ref) {\n            children.ref.current = node;\n        }\n    }",
    replace: "var _a;\n    if (children && ((_a = children.props) === null || _a === void 0 ? void 0 : _a.ref)) {\n        var ref = children.props.ref;\n        if ((0, is_1.isFunction)(ref)) {\n            ref(node);\n        }\n        if ('current' in ref) {\n            ref.current = node;\n        }\n    }\n    else if (children && children.ref) {\n        if ((0, is_1.isFunction)(children.ref)) {\n            children === null || children === void 0 ? void 0 : children.ref(node);\n        }\n        if ('current' in children.ref) {\n            children.ref.current = node;\n        }\n    }",
  },
  {
    file: "es/Trigger/index.js",
    search: "ref: popupChildren.ref",
    replace: "ref: (popupChildren.props && popupChildren.props.ref) ? popupChildren.props.ref : popupChildren.ref",
  },
  {
    file: "lib/Trigger/index.js",
    search: "ref: popupChildren.ref",
    replace: "ref: (popupChildren.props && popupChildren.props.ref) ? popupChildren.props.ref : popupChildren.ref",
  },
];

let patched = 0;
for (const p of patches) {
  const filePath = path.join(arcoRoot, p.file);
  try {
    let content = fs.readFileSync(filePath, "utf8");
    if (content.includes(p.search)) {
      content = content.replace(p.search, p.replace);
      fs.writeFileSync(filePath, content, "utf8");
      console.log(`[arco-react19-patch] Patched: ${p.file}`);
      patched++;
    } else if (content.includes(p.replace)) {
      console.log(`[arco-react19-patch] Already patched: ${p.file}`);
      patched++;
    } else {
      console.warn(`[arco-react19-patch] Pattern not found: ${p.file}`);
    }
  } catch (e) {
    console.warn(`[arco-react19-patch] Error patching ${p.file}:`, e.message);
  }
}
console.log(`[arco-react19-patch] Done: ${patched}/${patches.length} patches applied`);
