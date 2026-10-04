function ChatMessage({role,content}){


return (

<div 
className={
    role==="user"
    ?"message user"
    :"message ai"
}
>


<div className="avatar">

{
role==="user"
?"👤"
:"🤖"
}

</div>


<div className="bubble">

{content}

</div>


</div>


)

}


export default ChatMessage;