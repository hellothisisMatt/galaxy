<template>
    <invocations
        :invocationItems="invocationItems"
        :loading="loading"
        headerMessage="Your most recent workflow invocations are displayed on this page."
        noInvocationsMessage="There are no workflow invocations to show."
    >
    </invocations>
</template>

<script>
import Invocations from "../Workflow/Invocations";
import { getRecentInvocations } from "./UserServices";

export default {
    components: {
        Invocations
    },
    data() {
        return {
            invocationItems: [],
            loading: true
        };
    },
    created() {
        getRecentInvocations()
            .then(response => {
                this.invocationItems = response.data;
                this.loading = false;
            })
            .catch(this.handleError);
    },
    methods: {
        handleError(error) {
            console.error(error);
        }
    }
};
</script>
