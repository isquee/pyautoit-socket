import { Serializer } from 'autoit-serialize-js'

// arg[0] is the string to be unserialized to receive from autoit

const args = process.argv.slice(2);
if (args.length !== 1) {
    process.stderr.write("error, invalid amount of arguments")
}
const source = args[0]
const unserialized = Serializer.unSerialize(source)
const json = JSON.stringify(unserialized)
process.stdout.write(json)
