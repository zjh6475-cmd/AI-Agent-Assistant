import axios from "axios"

export const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL
    || "http://127.0.0.1:8000"


const service = axios.create({

    baseURL:API_BASE_URL,

    timeout:10000

})


// 请求拦截

service.interceptors.request.use(

    config=>{


        const token = localStorage.getItem("token")


        if(token){

            config.headers.Authorization =
            "Bearer " + token

        }


        return config

    },


    error=>{

        return Promise.reject(error)

    }

)





// 响应拦截

service.interceptors.response.use(


    response=>{


        return response.data


    },


    error=>{


        if(error.response){


            console.log(
                "错误:",
                error.response.data
            )


        }


        return Promise.reject(error)

    }

)



export default service