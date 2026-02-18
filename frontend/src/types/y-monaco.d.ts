declare module 'y-monaco' {
    import * as monaco from 'monaco-editor'
    import * as Y from 'yjs'
    import { Awareness } from 'y-protocols/awareness'

    export class MonacoBinding {
        constructor(
            ytext: Y.Text,
            model: monaco.editor.ITextModel,
            editors?: Set<monaco.editor.IStandaloneCodeEditor>,
            awareness?: Awareness | null
        )
        destroy(): void
    }
}
