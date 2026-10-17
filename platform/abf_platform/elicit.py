# Not a prompt inside the tool or a "confirm=true" argument: the model fills those in itself; a form of the MCP client is shown by the client and answered by the person at its screen, so the answer cannot come from the model.
"""Asking the person through the MCP client's own form (spec 009c).

A client that supports the MCP form request shows `message` to the person and returns what the person pressed. This module sends the
screen of a launch or a cancel with one yes/no field called 送出, and says yes only for an accepted answer whose 送出 is exactly true.
Declined, cancelled, no content, another content, a client that fails or goes away, and a form nobody answers in TIMEOUT_SECONDS are
all "no". The model that called the tool never sees a way to answer: nothing here takes an argument from the tool call but the screen.
"""
import anyio
from mcp.shared.exceptions import NoBackChannelError
from mcp_types import ClientCapabilities, ElicitationCapability, FormElicitationCapability
from pydantic import BaseModel, Field, StrictBool

TIMEOUT_SECONDS = 600.0


class SendForm(BaseModel):
    送出: StrictBool = Field(title="送出", description="按「是」才會送出（勾選 = 同意上面的全部內容）。 Tick to send exactly what is shown above.")


class Person:
    """The person behind one tool call, as far as this client can show forms."""

    def __init__(self, ctx):
        self._ctx = ctx

    def can_ask(self):
        try:
            return bool(self._ctx.request_context.session.check_client_capability(
                ClientCapabilities(elicitation=ElicitationCapability(form=FormElicitationCapability()))))
        except Exception:
            return False

    async def says_yes(self, screen_text):
        """(True, '') only for an accepted form with 送出 = true; otherwise (False, why). (None, why) when this call has no way to
        ask in the middle of it (a stateless connection): nobody was asked, and the page can be used instead."""
        try:
            with anyio.move_on_after(TIMEOUT_SECONDS) as scope:
                answer = await self._ctx.elicit(message=screen_text, schema=SendForm)
            if scope.cancelled_caught:
                return False, "no answer in time (逾時沒有回答)"
        except NoBackChannelError as e:
            return None, "this connection cannot show a form (這個連線不能跳出表單): %s" % e.__class__.__name__
        except Exception as e:      # the client failed, went away, or sent an answer that is not the form: that is no
            return False, "the form was not answered (沒有取得回答): %s" % e.__class__.__name__
        if answer.action == "accept" and getattr(getattr(answer, "data", None), "送出", None) is True:
            return True, ""
        return False, "the person did not say yes (本人沒有按送出): %s" % answer.action
