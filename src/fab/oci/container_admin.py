from hashlib import sha256

from ..model.oci import ImageNotFoundError, OciClient, OciContainer, OciError

CONTAINER_LABEL = "fab-build-container"


class ContainerAdmin:
    def __init__(self, client: OciClient):
        self.__client = client
        self.__container_store: dict[str, OciContainer] = dict()

    async def get_container(
        self,
        image: str,
        working_dir: str | None = None,
        cmd: list[str] | None = None,
        user: str | None = None,
        bind_mounts: list[tuple[str, str]] | None = None,
    ):

        key = sha256(str((image, cmd, user, bind_mounts)).encode()).hexdigest()

        if key in self.__container_store:
            return self.__container_store[key]

        container_name = f"fab_{key}"

        if container := await self.__client.find_container(name=container_name):
            self.__container_store[key] = container
            return container

        if not cmd:
            cmd = ["sleep", "infinity"]

        try:
            container = await self.__client.create_container(
                image,
                cmd,
                working_dir,
                user,
                bind_mounts,
                labels=[(CONTAINER_LABEL, "")],
                name=container_name,
            )
        except ImageNotFoundError:
            async for pull_event in self.__client.pull_image(image):
                print(pull_event)
                pass

            container = await self.__client.create_container(
                image,
                cmd,
                working_dir,
                user,
                bind_mounts,
                labels=[(CONTAINER_LABEL, "")],
                name=container_name,
            )

        await container.start()

        self.__container_store[key] = container
        return container

    async def clean_containers(self) -> int:
        containers = await self.__client.list_containers(label=(CONTAINER_LABEL, ""))
        for container in containers:
            try:
                await container.kill()
            except OciError:
                pass
            await container.remove()
        return len(containers)
