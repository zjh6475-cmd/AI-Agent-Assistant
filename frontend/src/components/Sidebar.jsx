import "./Sidebar.css"

import DocumentPanel from "./DocumentPanel"



function Sidebar({

    sessions,

    onSelectChat,

    onNewChat,

    onDeleteChat,

    onRenameChat,

    logout

}) {


    return (

        <aside className="sidebar">


            {/* 新建聊天按钮 */}

            <button

                type="button"

                className="new-chat"

                onClick={onNewChat}

            >

                + 新聊天

            </button>



            {/* 历史聊天区域 */}

            <section className="sidebar-section">


                <div className="history-title">

                    历史聊天

                </div>



                <div className="history-list">


                    {

                        (sessions || []).length === 0

                            ? (

                                <div className="history-empty">

                                    暂无聊天记录

                                </div>

                            )

                            : (

                                (sessions || []).map(item => (

                                    <div

                                        key={item.id}

                                        className="history-item"

                                    >


                                        {/* 聊天标题 */}

                                        <button

                                            type="button"

                                            className="history-name"

                                            title={item.title}

                                            onClick={() =>
                                                onSelectChat(item.id)
                                            }

                                        >

                                            {item.title}

                                        </button>



                                        {/* 操作按钮 */}

                                        <div className="history-actions">


                                            <button

                                                type="button"

                                                className="history-action-button"

                                                onClick={event => {

                                                    event.stopPropagation()

                                                    onRenameChat(item)

                                                }}

                                            >

                                                修改

                                            </button>



                                            <button

                                                type="button"

                                                className="history-action-button delete-button"

                                                onClick={event => {

                                                    event.stopPropagation()

                                                    onDeleteChat(item.id)

                                                }}

                                            >

                                                删除

                                            </button>


                                        </div>


                                    </div>

                                ))

                            )

                    }


                </div>


            </section>



            {/* 文件上传和文件列表 */}

            <section className="document-section">

                <DocumentPanel />

            </section>



            {/* 用户信息 */}

            <footer className="sidebar-footer">


                <div className="sidebar-user">

                    用户：

                    <span>

                        {
                            localStorage.getItem("username")
                            || "未登录"
                        }

                    </span>

                </div>



                <button

                    type="button"

                    className="logout-button"

                    onClick={logout}

                >

                    退出登录

                </button>


            </footer>


        </aside>

    )

}



export default Sidebar