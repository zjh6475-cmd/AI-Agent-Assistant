import {
    useEffect,
    useRef,
    useState
} from "react"

import request from "../api/request"

import "./DocumentPanel.css"



function DocumentPanel() {


    // 当前用户上传的文件列表
    const [documents, setDocuments] = useState([])


    // 当前选择的文件
    const [selectedFile, setSelectedFile] = useState(null)


    // 是否正在上传
    const [uploading, setUploading] = useState(false)


    // 当前正在删除的文件ID
    const [deletingId, setDeletingId] = useState(null)


    // 文件输入框
    const fileInputRef = useRef(null)



    // =========================
    // 获取当前用户文件列表
    // =========================

    const loadDocuments = async () => {


        try {


            const res = await request.get(
                "/documents"
            )


            setDocuments(

                Array.isArray(res)

                    ? res

                    : []

            )


        } catch (error) {


            console.log(
                "获取文件列表失败：",
                error
            )


            setDocuments([])

        }

    }



    // 页面加载时获取文件列表

    useEffect(() => {


        loadDocuments()


    }, [])



    // =========================
    // 选择文件
    // =========================

    const selectFile = event => {


        const file =
            event.target.files?.[0]


        if (!file) {


            setSelectedFile(null)

            return

        }


        setSelectedFile(file)

    }



    // =========================
    // 上传文件
    // =========================

    const uploadFile = async () => {


        if (!selectedFile) {


            alert("请先选择文件")

            return

        }



        const formData = new FormData()


        // 必须使用 file
        // 对应后端参数：
        // file: UploadFile

        formData.append(
            "file",
            selectedFile
        )



        try {


            setUploading(true)



            const res = await request.post(

                "/documents/upload",

                formData,

                {
                    timeout: 60000
                }

            )



            alert(
                res.message || "上传成功"
            )



            // 清空已选择文件

            setSelectedFile(null)



            // 清空input显示

            if (fileInputRef.current) {


                fileInputRef.current.value = ""

            }



            // 上传成功后刷新文件列表

            await loadDocuments()



        } catch (error) {


            console.log(
                "上传文件失败：",
                error
            )


            alert(

                error.response?.data?.detail

                || "上传失败"

            )


        } finally {


            setUploading(false)

        }

    }



    // =========================
    // 删除文件
    // =========================

    const deleteDocument = async item => {


        const confirmed = window.confirm(

            `确定删除文件“${item.filename}”吗？\n\n删除后，该文件将无法继续用于知识库检索。`

        )


        if (!confirmed) {


            return

        }



        try {


            setDeletingId(item.id)



            const res = await request.delete(

                `/documents/${item.id}`

            )



            alert(
                res.message || "删除成功"
            )



            // 删除成功后刷新列表

            await loadDocuments()



        } catch (error) {


            console.log(
                "删除文件失败：",
                error
            )


            alert(

                error.response?.data?.detail

                || "删除失败"

            )


        } finally {


            setDeletingId(null)

        }

    }



    return (

        <div className="document-panel">


            {/* 标题 */}

            <div className="document-title">

                知识文件

            </div>



            {/* 文件选择 */}

            <input

                ref={fileInputRef}

                className="document-input"

                type="file"

                accept=".pdf,.txt,.docx"

                onChange={selectFile}

                disabled={uploading}

            />



            {/* 已选择文件 */}

            {

                selectedFile && (

                    <div className="selected-file">

                        已选择：

                        <span>

                            {selectedFile.name}

                        </span>

                    </div>

                )

            }



            {/* 上传按钮 */}

            <button

                type="button"

                className="upload-button"

                onClick={uploadFile}

                disabled={

                    uploading

                    || !selectedFile

                }

            >

                {

                    uploading

                        ? "上传中..."

                        : "上传文件"

                }

            </button>



            {/* 文件列表 */}

            <div className="document-list">


                {

                    documents.length === 0

                        ? (

                            <div className="document-empty">

                                暂无文件

                            </div>

                        )

                        : documents.map(item => (


                            <div

                                key={item.id}

                                className="document-item"

                            >


                                {/* 文件主要信息 */}

                                <div className="document-main">


                                    <div

                                        className="document-name"

                                        title={item.filename}

                                    >

                                        📄 {item.filename}

                                    </div>



                                    <div className="document-info">


                                        {

                                            item.file_type
                                                ?.toUpperCase()

                                        }


                                        {

                                            item.create_time && (

                                                <span>

                                                    {" · "}

                                                    {

                                                        new Date(
                                                            item.create_time
                                                        )
                                                        .toLocaleDateString()

                                                    }

                                                </span>

                                            )

                                        }


                                    </div>


                                </div>



                                {/* 删除按钮 */}

                                <button

                                    type="button"

                                    className="document-delete-button"

                                    disabled={
                                        deletingId === item.id
                                    }

                                    onClick={() =>
                                        deleteDocument(item)
                                    }

                                >

                                    {

                                        deletingId === item.id

                                            ? "删除中"

                                            : "删除"

                                    }

                                </button>


                            </div>


                        ))

                }


            </div>


        </div>

    )

}



export default DocumentPanel