import {
useState
} from "react"


import Login from "./components/Login"

import Register from "./components/Register"

import Layout from "./components/Layout"





function App(){



const [page,setPage]=useState("login")





return(


<div className="app">



{

page==="login"


?


<Login

setPage={setPage}

/>


:

page==="register"


?


<Register

setPage={setPage}

/>



:


<Layout

setPage={setPage}

/>


}




</div>


)



}



export default App