from plugp100.common.functional.tri import Try
from plugp100.requests.tapo_request import TapoRequest
from plugp100.responses.tapo_response import TapoResponse


class TapoResponseMockHelper:
    def __init__(self, data: dict[str, Try[TapoResponse]]) -> None:
        self.data = data

    async def get_response(
        self, request: TapoRequest, child_id: str = ""
    ) -> Try[TapoResponse]:
        if request.method == "control_child":
            return await self.get_response(
                request.params.requestData.params.requests[0],
                f"_{request.params.device_id}",
            )

        response = self.data.get(
            f"{request.method}{child_id}", Try.of(TapoResponse(0, {}, None))
        )
        if child_id != "":
            return tapo_response_child_of(response.get().result)
        return response


def tapo_response_of(payload: dict[str, any]) -> Try[TapoResponse]:
    return Try.of(TapoResponse(error_code=0, result=payload, msg=""))


def tapo_response_child_of(payload: dict[str, any]) -> Try[TapoResponse]:
    return tapo_response_of(
        {"responseData": {"result": {"responses": [{"result": payload}]}}}
    )
