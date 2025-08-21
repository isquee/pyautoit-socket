import { Serializer } from 'autoit-serialize-js'

// arg[0] is the string to be serialized to send to autoit

const args = process.argv.slice(2);
if (args.length !== 1) {
    process.stderr.write("error, invalid amount of arguments")
}
const source = args[0]
const json = JSON.parse(source)
const serialized = Serializer.serialize(json)
process.stdout.write(serialized)
