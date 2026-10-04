import request from "./request"



// 获取聊天列表

export function getSessions(){

    return request.get(
        "/sessions"
    )

}




// 创建聊天

export function createSession(){

    return request.post(
        "/session/new"
    )

}




// 修改标题

export function updateSession(
    id,
    title
){

    return request.put(

        `/session/${id}`,

        {
            title:title
        }

    )

}




// 删除聊天

export function deleteSession(id){

    return request.delete(

        `/session/${id}`

    )

}
