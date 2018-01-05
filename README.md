# ShadowChain
*本项目为杭州电子科技大学通信工程学院大学生科研创新训练计划项目课题,仅供学习交流之用*
From The Shadow  : )

## 项目初衷
此项目的本意是建立一个自动化，高度匿名的代理工具。项目特点如下：
1. 项目使用python3.4之后引入的asyncio包完成，所有io交互实现异步。所有io操作都在单一线程中完成
2. 项目引入协议栈机制，可以任意扩展第三方协议。并且通过协议栈，可以完成将单一数据包裹复数协议的方式传送。达到链式代理的目的。
3. 入上所言，项目可以任意扩展协议的数量，通过后续开发，可以支持复数协议。


## 协议开发
协议可以抽象的分成两种，server协议和client协议。程序运行时会使用一种server协议来监听某端口。作为代理数据的输入。client协议端支持复数的协议栈，通过回调函数的方式层级传播数据。

### 入口协议
由于是瞎写着玩，开发接口耦合严重。撸协议自己阅读`protocol.BaseServer`源码。此类继承自[asyncio.Protocol](https://docs.python.org/3/library/asyncio-protocol.html#protocols)。所以支持protocol中所有回调。

> BaseServer.loop

创建类的时候传入的event_loop实例，异步调用会使用此loop

> BaseServer.transport

connection_made时传入的和此protocol对应的transport方法。请及时保存。

> BaseServer.peer_transport

这个东西是对端，也就是client端的transport实例，不过不推荐直接读写，所有数据因通过协议栈打包发送

> BaseServer.peer_proto

client端协议的实例，为`BaseClientTop`类。协议栈入口。

> BaseServer.write(self, data)

当client端有数据到来的时候会调用此方法。

> BaseServer.connection_lost(self, exc)

类中有一些默认操作，重载时请保留

> BaseServer.handle_peer_close

当对端关闭的时候会调用此方法，表示如何处理此问题。默认方法是调用raw_close()

> BaseServer.notify_ignore

设置为True，则`handle_peer_close`不会被调用。

> BaseServer.raw_close(result)

由于在close中有特殊处理(通知协议链中其他协议)，以及其他处理。提供raw_close函数来清理资源。raw会在close以及默认的connection_lose中调用.result参数表示关闭原因，暂时为None

### 出口协议
获取出口协议使用`baseRoute`包中的
> async def out_protocol_chains(host, port, loop, in_protocol):

传入参数是转发的目标位置，目标端口，当前使用的event_loop还有入口协议本身。

出口协议可以从`baseRoute.BaseClient`继承而来。

> baseRoute.BaseClient(loop, prev_proto, origin_host, origin_port)

loop为传入的lopp，prev_proto为协议栈的上一层协议，origin为原始转发目标，origin_port为原始转发端口。
当然由于协议栈中某一层协议具体发送向那个ip还是由配置文件制定的。这里的origin_host和origin_port作为备份。当然如果是最上层协议，还是需要使用这两个参数的。参数放在对应名字的类属性内。

> BaseClient.connection_made(transport, next_proto)

次函数由下层的协议调用。下层协议处理完连接和协议交互之后，调用此函数。next_proto和transport需要保存在对应名字的属性中。
接受到此回调之后，可以开始本协议层的协商和交互。协商结束之后调用prev_proto的connection_make通知上层协议。

> BaseClient.data_received(data)

提示下层协议有数据到来。处理完成之后可以调用上层协议的data_received以通知上层

> BaseClient.write(data)

表示上层有数据到来。

> BaseClient.close(self, result=None)

同样不建议重载，使用raw_close

>BaseClient.handle_peer_close

当协议栈中某一协议声明关闭时会调用此方法，表示如何处理此问题。默认方法是调用raw_close()

>BaseClient.notify_ignore

设置为True，则`handle_peer_close`不会被调用。

写好的协议栈只需要按照从上到下的顺序写入context的protocol_chains列表中即可。实例化时只会传入BaseClient中默认参数。其他参数可以使用偏函数传入。

## 目前支持的协议与将要实现的协议
1. ### sock5
普通的sock5协议。目前只支持ipv4， connect方法。其他部分之之后完善

2. ### SC
shadow chain的私有协议。0.01版本协议手册见项目中SC协议文档部分
