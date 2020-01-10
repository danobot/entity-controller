var v = require('./package.json').version
const replace = require('replace-in-file');
const regex = new RegExp('VERSION = .*', 'i');
const options = {
    files: 'custom_components/entity_controller/__init__.py',
    from: regex,
    to: "VERSION = '"+v+"'",
};

var changes = replace.sync(options)



const regex3 = new RegExp('Version:          .*', 'i');

const header_version = {
    files: 'custom_components/entity_controller/__init__.py',
    from: regex3,
    to: "Version:          v"+v,
};
changes = replace.sync(header_version)

console.log("chore(release): " + v)
