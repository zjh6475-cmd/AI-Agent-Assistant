import {useState} from "react"
import "./Login.css"
import request from "../api/request"



function Login({setPage}){


const [username,setUsername]=useState("")

const [password,setPassword]=useState("")





const login=async()=>{


try{


const res=await request.post(       

"/login",

{
username,
password
}

)
console.log("登录返回:",res.data)
// 对应后端登录的接口


if(!res.token){


alert(
res.message || "账号密码错误"
)

return


}




localStorage.setItem(

"token",

res.token   //前端保存token

)
localStorage.setItem(
    "username",
    res.username
)



alert("登录成功")


setPage("chat")



}catch(error){


console.log(error)

alert("登录失败")


}



}





return(


<div className="login-container">


<h2>
AI Agent 登录
</h2>



<input

placeholder="用户名"

value={username}

onChange={
e=>setUsername(e.target.value)
}


/>


<br/>


<input

type="password"

placeholder="密码"

value={password}

onChange={
e=>setPassword(e.target.value)
}


/>



<br/>


<button

onClick={login}

>

登录

</button>



<br/>


<button

onClick={()=>setPage("register")}

>

注册账号

</button>



</div>



)



}


export default Login