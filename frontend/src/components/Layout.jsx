import {
useState,
useEffect
} from "react"


import Sidebar from "./Sidebar"

import Chat from "./Chat"

import request from "../api/request"

import "./Layout.css"





function Layout({setPage}){


const [chatList,setChatList]=useState([])


const [sessions,setSessions]=useState([])


const [sessionId,setSessionId]=useState(null)





useEffect(()=>{


const token=localStorage.getItem("token")


if(!token){

setPage("login")

return

}


loadSessions()


},[])





// 获取聊天列表

const loadSessions=async()=>{


try{


const res=await request.get(
"/sessions"
)

console.log("sessions返回:",res)
setSessions(res)


}catch(error){


console.log(error)


}


}






// 新聊天

const newChat=async()=>{


try{


const res=await request.post(
"/session/new"
)


setSessionId(
    res.id
)


setChatList([])



loadSessions()



}catch(error){


console.log(error)


}


}






// 点击聊天

const selectChat=async(id)=>{


try{


const res=await request.get(

"/history/"+id

)



setChatList(res)


setSessionId(id)



}catch(error){

console.log(error)

}


}






// 删除聊天

const deleteChat=async(id)=>{


const confirmDelete = window.confirm(
    "确定要删除这个聊天吗？删除后无法恢复"
)


if(!confirmDelete){

    return

}



try{


await request.delete(

`/session/${id}`

)



if(sessionId===id){

setChatList([])

setSessionId(null)

}



loadSessions()



}catch(error){


console.log(error)


}


}











// 修改标题

const renameChat=async(item)=>{


const title=prompt(

"请输入新的标题",

item.title

)


if(!title){

return

}



try{


await request.put(

`/session/${item.id}`,

{

title:title

}

)



loadSessions()



}catch(error){


console.log(error)


}


}








//退出登录

const logout=()=>{


const confirmLogout = window.confirm(
    "确定退出登录吗？"
)


if(!confirmLogout){

    return

}



localStorage.removeItem("token")

localStorage.removeItem("username")


setPage("login")


}








return(


<div className="layout">



<Sidebar


sessions={sessions}


onNewChat={newChat}


onSelectChat={selectChat}


onDeleteChat={deleteChat}


onRenameChat={renameChat}


logout={logout}


/>




<Chat


chatList={chatList}


setChatList={setChatList}


sessionId={sessionId}


setSessionId={setSessionId}


loadSessions={loadSessions}


/>



</div>


)



}



export default Layout