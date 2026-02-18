import { useEditorStore } from '../store/editorStore'

const UserPresence = () => {
    const { users, isConnected } = useEditorStore()

    return (
        <div className="flex items-center gap-3 px-4 py-2 bg-slate-800 border-b border-slate-700">
            {/* Connection Status */}
            <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success animate-pulse' : 'bg-gray-500'}`} />
                <span className="text-sm text-gray-300">
                    {isConnected ? 'Connected' : 'Disconnected'}
                </span>
            </div>

            {/* User Avatars */}
            {users.length > 0 && (
                <>
                    <div className="w-px h-4 bg-slate-600" />
                    <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-400">Collaborators:</span>
                        <div className="flex -space-x-2">
                            {users.map((user) => (
                                <div
                                    key={user.id}
                                    className="w-8 h-8 rounded-full border-2 border-slate-800 flex items-center justify-center text-xs font-semibold text-white"
                                    style={{ backgroundColor: user.color }}
                                    title={user.name}
                                >
                                    {user.name.charAt(0).toUpperCase()}
                                </div>
                            ))}
                        </div>
                    </div>
                </>
            )}
        </div>
    )
}

export default UserPresence
