from langgraph.store.memory import InMemoryStore


# 创建一个内存 Store
store = InMemoryStore()


def save_user_name(
    user_id: str,
    name: str
):
    """
    保存用户的长期记忆。
    """

    namespace = (
        user_id,
        "memories"
    )

    store.put(
        namespace,
        "user_name",
        {
            "name": name
        }
    )

    print("已保存用户姓名：", name)


def read_user_name(
    user_id: str
):
    """
    读取用户的长期记忆。
    """

    namespace = (
        user_id,
        "memories"
    )

    item = store.get(
        namespace,
        "user_name"
    )

    if item is None:
        print("没有找到用户姓名")
        return None

    name = item.value["name"]

    print("读取到用户姓名：", name)

    return name


def run_thread(
    thread_id: str,
    user_id: str,
    question: str
):
    """
    模拟不同 thread 中的对话。
    """

    print()
    print("当前线程：", thread_id)
    print("用户问题：", question)

    if question.startswith("我叫"):
        name = question[2:].strip()

        save_user_name(
            user_id,
            name
        )

        print("AI：我记住了，你叫", name)

    elif question in ("我叫什么", "我叫什么？"):
        name = read_user_name(user_id)

        if name:
            print("AI：你叫", name)
        else:
            print("AI：我还不知道你的名字")

    else:
        print("AI：这是一个普通问题")


if __name__ == "__main__":

    # thread-1 中保存用户姓名
    run_thread(
        thread_id="thread-1",
        user_id="user-1",
        question="我叫小黄"
    )

    # 换成 thread-2，但仍然是 user-1
    run_thread(
        thread_id="thread-2",
        user_id="user-1",
        question="我叫什么？"
    )

    # 换成 user-2
    run_thread(
        thread_id="thread-3",
        user_id="user-2",
        question="我叫什么？"
    )