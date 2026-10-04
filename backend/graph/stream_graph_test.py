from graph.project_graph import stream_agent_graph


if __name__ == "__main__":
    for part in stream_agent_graph(
        user_id=1,
        session_id=9999,
        question="请用一句话解释什么是 Python。",
    ):
        event_type = part["type"]

        # 模型真正逐段生成的内容
        if event_type == "messages":
            message_chunk, metadata = part["data"]

            content = message_chunk.content

            if isinstance(content, str) and content:
                print(
                    content,
                    end="",
                    flush=True,
                )

        # 每个节点完成后产生的状态更新
        elif event_type == "updates":
            for node_name, update in part["data"].items():
                for step in update.get("steps", []):
                    print()
                    print(
                        f"\n[步骤] {node_name}："
                        f"{step['message']}"
                    )
                    
                            # 工具临时失败时，由 stream_writer 写出的自定义事件
        elif event_type == "custom":
            data = part["data"]

            if (
                isinstance(data, dict)
                and data.get("type") == "tool_retry"
            ):
                print()
                print(
                    f"[重试] {data['message']}"
                )

        # Graph 已到 END
        elif event_type == "final_state":
            print("\n\n[Graph 已完成]")
            print(
                "消息数量：",
                len(part["data"]["messages"]),
            )