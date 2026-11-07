import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,readdirSync} from 'node:fs';
// TypeScript permits arbitrary strings here; the Android setter throws for unknown roles.
const native=readFileSync(new URL('../node_modules/react-native/ReactAndroid/src/main/java/com/facebook/react/uimanager/ReactAccessibilityDelegate.kt',import.meta.url),'utf8');
function roles(name:string):Set<string>{
 const block=native.match(new RegExp(`enum class ${name} \\{([\\s\\S]*?);`));
 assert.ok(block,'Android role enum must be inspectable');
 return new Set([...block[1].matchAll(/^[ \t]*([A-Z][A-Z0-9_]*)[,;]/gm)].map(m=>m[1].toLowerCase()));
}
test('screen roles are accepted by the installed Android native setters',()=>{
 const allowed=roles('AccessibilityRole'),aria=roles('Role');
 const files=['App.tsx',...readdirSync(new URL('../src/',import.meta.url)).filter(f=>f.endsWith('.tsx')).map(f=>'src/'+f)];
 let checked=0;
 for(const file of files){const text=readFileSync(new URL('../'+file,import.meta.url),'utf8');
  for(const m of text.matchAll(/\b(accessibilityRole|role)="([^"]+)"/g)){
   assert.ok((m[1]==='role'?aria:allowed).has(m[2]),`${file}: native ${m[1]} rejects ${m[2]}`);checked++;
  }
 }
 assert.ok(checked>10);
 assert.equal(allowed.has('status'),false,'status must use role, not accessibilityRole');
 assert.equal(aria.has('status'),true);
});
