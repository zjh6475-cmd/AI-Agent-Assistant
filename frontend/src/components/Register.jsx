import {
    useState
} from "react"


import request from "../api/request"
import "./Register.css"


function Register({setPage}){


    const [username,setUsername]=useState("")

    const [password,setPassword]=useState("")

    const [confirmPassword,setConfirmPassword]=useState("")





    const register=async()=>{


        if(!/^\d{11}$/.test(username)){


            alert(
                "账号必须是11位数字"
            )

            return

        }



        if(password!==confirmPassword){


            alert(
                "两次密码不一致"
            )

            return

        }





        try{


            const res=await request.post(

                "/register",

                {

                    username,

                    password,

                    confirm_password:
                    confirmPassword

                }

            )

            console.log("注册返回:",res)



            alert(
                res.message
            )



            if(
                res.message==="注册成功"
            ){

                setPage("login")

            }



        }catch(error){


            console.log(error)

            alert(
                "注册失败"
            )


        }


    }






    return(

        <div className="register-container">


            <h2>

                AI Agent 注册

            </h2>




            <input

            placeholder="11位数字账号"

            value={username}

            onChange={
                e=>setUsername(e.target.value)
            }


            />



            <br/>





            <input

            placeholder="密码"

            type="password"

            value={password}

            onChange={
                e=>setPassword(e.target.value)
            }


            />



            <br/>




            <input

            placeholder="再次输入密码"

            type="password"

            value={confirmPassword}

            onChange={
                e=>setConfirmPassword(e.target.value)
            }


            />



            <br/>





            <button

            onClick={register}

            >

                注册

            </button>



            <button

            onClick={
                ()=>setPage("login")
            }

            >

                返回登录

            </button>



        </div>

    )

}



export default Register