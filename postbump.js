var v = require('./package.json').version
console.log(v);
const replace = require('replace-in-file');
const regex = new RegExp('VERSION = .*', 'i');
const options = {
    files: 'custom_components/lightingsm.py',
    from: regex,
    to: "VERSION = '"+v+"'",
};

var changes = replace.sync(options)

console.log(changes.join())


const regex2 = new RegExp('"version": .*', 'i');

const options2 = {
    files: 'tracker.json',
    from: regex2,
    to: "\"version\": \""+v+"\",",
};
changes = replace.sync(options2)

console.log(changes.join())

// Header



const regex3 = new RegExp('Version:          .*', 'i');

const lightingsm_header = {
    files: 'custom_components/lightingsm.py',
    from: regex3,
    to: "Version:          v"+v,
};
changes = replace.sync(lightingsm_header)

console.log(changes.join())
